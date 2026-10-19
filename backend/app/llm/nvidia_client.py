"""NVIDIA NIM isteklerini süre sınırı, hata yönetimi ve model seçimiyle yürütür."""

import asyncio  # Asenkron bekleme ve toplam işlem süresi sınırı için kullanılır.
import logging  # Başarı, hata ve uyarı kayıtlarını yazmak için kullanılır.
import re  # İstek kimliğini düzenli ifadeyle kontrol etmek için kullanılır.
from dataclasses import dataclass  # Veri sınıfının kurucu gibi metotlarını otomatik oluşturur.
from enum import StrEnum  # Metin değerleri taşıyan enum sınıfının temelidir.
from time import perf_counter  # İşlemlerin süresini ölçmek için hassas sayaç sağlar.

import httpx  # HTTP bağlantısındaki farklı zaman aşımı ayarlarını oluşturur.
from openai import (
    APIConnectionError,  # SDK'nın bağlantı hatası türüdür.
    APITimeoutError,  # SDK'nın zaman aşımı hatası türüdür.
    AsyncOpenAI,  # NVIDIA'nın uyumlu API'sine bağlanacak asenkron istemcidir.
    OpenAIError,  # SDK hatalarını ortak bir tür üzerinden yakalamayı sağlar.
)

from app.config import Settings  # Uygulamanın yapılandırma sınıfını getirir.
from app.llm.nvidia_options import get_model_options  # Modele özel istek seçeneklerini getirir.
from app.llm.prompt_builder import (
    build_repair_messages,  # Hatalı kodu düzeltmek için gönderilecek mesajları hazırlar.
    build_strategy_messages,  # İlk strateji üretimi için gönderilecek mesajları hazırlar.
)
from app.llm.repair_context import RepairFailureContext  # Düzeltme aşamasına taşınan hata bağlamıdır.

logger = logging.getLogger(__name__)  # Bu modülün adıyla bir log nesnesi oluşturur.


# KALITIM: StrEnum'dan türeyerek metin değerli, sabit hata kategorileri tanımlar.
class ProviderErrorKind(StrEnum):
    AUTHENTICATION = "authentication_failure"  # API anahtarı veya kimlik doğrulama hatasıdır.
    PERMISSION = "permission_denied"  # İstenen işlem için erişim izni bulunmadığını belirtir.
    MODEL_UNAVAILABLE = "model_unavailable"  # Modelin kullanılamadığını belirtir.
    RATE_LIMIT = "provider_rate_limit"  # Sağlayıcının istek sınırına ulaşıldığını belirtir.
    TIMEOUT = "provider_timeout"  # İsteğin zaman sınırını aştığını belirtir.
    SERVER = "provider_5xx"  # Sağlayıcının sunucu tarafındaki hatasını belirtir.
    NETWORK = "network_failure"  # Ağ veya bağlantı hatasını belirtir.
    INVALID_REQUEST = "invalid_request"  # Sağlayıcının geçersiz bulduğu isteği belirtir.
    INVALID_RESPONSE = "invalid_response"  # Boş veya kullanılamayan yanıtı belirtir.
    UNKNOWN = "provider_error"  # Diğer kategorilere ayrılamayan hatayı belirtir.


# KALITIM: RuntimeError'dan türeyerek projeye özel bir exception tanımlar.
class NvidiaNimError(RuntimeError):
    """Kontrollü bir hata mesajı ve makine tarafından okunabilir kategori taşır."""

    def __init__(
        self,  # Oluşturulmakta olan hata nesnesidir.
        message: str,  # Hata nesnesinin taşıyacağı açıklamadır.
        *,  # Sonraki argümanların isimleriyle verilmesini zorunlu kılar.
        kind: ProviderErrorKind = ProviderErrorKind.UNKNOWN,  # Varsayılan hata kategorisidir.
    ):
        super().__init__(message)  # Üst sınıf RuntimeError'ın kurucusuna mesajı aktarır.
        self.kind = kind  # Ek kategori bilgisini hata nesnesinde saklar.


@dataclass(frozen=True)  # Veri metotlarını üretir; alanların normal atamayla değiştirilmesini engeller.
class ProviderErrorDetails:
    exception_type: str  # Orijinal hatanın Python sınıf adını saklar.
    status_code: int | None  # HTTP durum kodunu veya kod yoksa None değerini saklar.
    request_id: str | None  # Filtrelenmiş istek kimliğini veya None değerini saklar.
    message: str  # Ham sağlayıcı metni yerine kontrollü hata mesajını saklar.
    kind: ProviderErrorKind  # Hatanın uygulama içindeki kategorisini saklar.

    def as_text(self) -> str:  # Hata bilgilerini loga yazılacak tek bir metne dönüştürür.
        return (
            f"category={self.kind.value} type={self.exception_type} "  # Kategori ve sınıf adını ekler.
            f"status={self.status_code if self.status_code is not None else '-'} "  # Kod yoksa - yazar.
            f"request_id={self.request_id or '-'} message={self.message}"  # Kimlik ve mesajı ekler.
        )


def get_provider_error_details(
    error: OpenAIError | TimeoutError,  # Sınıflandırılacak hata nesnesini alır.
    *,  # api_key argümanının adıyla verilmesini zorunlu kılar.
    api_key: str = "",  # İstek kimliğinde anahtar sızıntısı kontrolü için kullanılır.
) -> ProviderErrorDetails:  # Sonuç olarak düzenlenmiş hata bilgilerini döndürür.
    """Hata türünü ve durum kodunu sınıflandırır; ham sağlayıcı mesajını saklamaz."""

    status = getattr(error, "status_code", None)  # Alan varsa durum kodunu, yoksa None alır.

    if isinstance(error, (APITimeoutError, TimeoutError)):  # Önce zaman aşımı türlerini kontrol eder.
        kind = ProviderErrorKind.TIMEOUT  # Zaman aşımı kategorisini seçer.
    elif status == 401:  # HTTP 401 kimlik doğrulama hatasıdır.
        kind = ProviderErrorKind.AUTHENTICATION  # Kimlik doğrulama kategorisini seçer.
    elif status == 403:  # HTTP 403 erişimin reddedildiğini belirtir.
        kind = ProviderErrorKind.PERMISSION  # İzin kategorisini seçer.
    elif status in (404, 410):  # Bu kodları modelin kullanılamaması olarak yorumlar.
        kind = ProviderErrorKind.MODEL_UNAVAILABLE  # Model kullanılamıyor kategorisini seçer.
    elif status == 429:  # HTTP 429 istek sınırına takılmayı belirtir.
        kind = ProviderErrorKind.RATE_LIMIT  # İstek sınırı kategorisini seçer.
    elif status is not None and 500 <= status <= 599:  # Durum kodunun 5xx olup olmadığına bakar.
        kind = ProviderErrorKind.SERVER  # Sağlayıcı sunucu hatası kategorisini seçer.
    elif isinstance(error, APIConnectionError):  # SDK'nın bağlantı hatası olup olmadığına bakar.
        kind = ProviderErrorKind.NETWORK  # Ağ hatası kategorisini seçer.
    elif status is not None and 400 <= status <= 499:  # Geriye kalan 4xx hatalarını yakalar.
        kind = ProviderErrorKind.INVALID_REQUEST  # Geçersiz istek kategorisini seçer.
    else:  # Hiçbir özel koşula uymayan hataları ele alır.
        kind = ProviderErrorKind.UNKNOWN  # Genel hata kategorisini seçer.

    request_id = getattr(error, "request_id", None)  # Varsa sağlayıcının istek kimliğini alır.

    if (
        not isinstance(request_id, str)  # İstek kimliği metin değilse kabul etmez.
        or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id)  # Biçim ve uzunluk şartını denetler.
        or "nvapi-" in request_id  # NVIDIA anahtarı öneki içeren kimliği kabul etmez.
        or (api_key and api_key in request_id)  # Gerçek API anahtarını içeren kimliği kabul etmez.
    ):
        request_id = None  # Kontrolden geçemeyen kimliği tamamen kaldırır.

    return ProviderErrorDetails(
        type(error).__name__,  # Hatanın sınıf adını ekler.
        status,  # HTTP durum kodunu ekler.
        request_id,  # Yalnız kontrolden geçen istek kimliğini ekler.
        "Provider request failed.",  # Ham hata metni yerine sabit mesaj kullanır.
        kind,  # Belirlenen hata kategorisini ekler.
    )


# Bu sınıf AsyncOpenAI'dan türemez; içinde bir AsyncOpenAI nesnesi tutar: bileşim.
class NvidiaNimClient:
    """Üretim, yeniden deneme ve düzeltme boyunca kullanılabilen istemciyi yönetir."""

    def __init__(self, settings: Settings) -> None:  # Nesne oluşturulurken ayarları alır.
        self._settings = settings  # Ayar nesnesini daha sonra kullanmak için saklar.
        self._client: AsyncOpenAI | None = None  # API istemcisini henüz oluşturmaz.
        self._last_model = settings.nvidia_model  # Başlangıç model bilgisini ana modelden alır.
        self._managed = False  # Henüz async with bağlamına girilmediğini işaretler.

    @property  # model metoduna client.model biçiminde erişilmesini sağlar.
    def model(self) -> str:  # Saklanan model bilgisini okumaya açar.
        """Başarılı yanıttaki modeli; başarı öncesinde başlangıç modelini döndürür."""
        return self._last_model  # Son kaydedilen model adını döndürür.

    async def __aenter__(self):  # async with bloğuna girildiğinde otomatik çağrılır.
        # İstemciyi burada açmaz; anahtar kontrolünü üretim aşamasına bırakır.
        self._managed = True  # Bağlamın başladığını işaretler.
        return self  # async with ... as client içindeki değişkene bu nesneyi verir.

    def _open_client(self) -> None:  # Gerçek API istemcisini ihtiyaç anında oluşturur.
        api_key = self._settings.nvidia_api_key.get_secret_value().strip()  # Anahtarı alıp kırpar.

        if not api_key:  # Anahtar yoksa veya yalnız boşluklardan oluşuyorsa bu kola girer.
            raise NvidiaNimError(
                "NVIDIA API anahtarı yapılandırılmamış.",  # Kontrollü hata açıklamasıdır.
                kind=ProviderErrorKind.AUTHENTICATION,  # Eksik anahtarı kimlik hatası sayar.
            )

        self._client = AsyncOpenAI(
            api_key=api_key,  # İsteklerde kullanılacak anahtarı istemciye verir.
            base_url=self._settings.nvidia_base_url,  # İstekleri NVIDIA adresine yönlendirir.
            timeout=httpx.Timeout(
                connect=self._settings.nvidia_connect_timeout_seconds,  # Bağlanma süresi sınırıdır.
                read=self._settings.nvidia_read_timeout_seconds,  # Veri okuma bekleme sınırıdır.
                write=self._settings.nvidia_write_timeout_seconds,  # Veri gönderme bekleme sınırıdır.
                pool=self._settings.nvidia_pool_timeout_seconds,  # Havuzdan bağlantı bekleme sınırıdır.
            ),
            max_retries=0,  # SDK tekrarlarını kapatır; tekrarları bu sınıf yönetecektir.
        )

    async def __aexit__(
        self,  # Bağlamından çıkılan istemci nesnesidir.
        exc_type,  # Blokta hata oluştuysa hatanın türüdür.
        exc,  # Blokta hata oluştuysa hata nesnesidir.
        traceback,  # Blokta hata oluştuysa hata izidir.
    ) -> None:  # async with bloğundan çıkarken kaynakları temizler.
        client, self._client = self._client, None  # Eski istemciyi alır, nesnedeki alanı boşaltır.
        self._managed = False  # Bağlamın sona erdiğini işaretler.

        if client is not None:  # Gerçekten bir API istemcisi oluşturulmuşsa kapatır.
            await client.close()  # İstemcinin bağlantı kaynaklarını asenkron biçimde kapatır.

    async def generate_code(self, prompt: str) -> str:  # İlk üretim için dışarıya açık metottur.
        return await self._complete(
            build_strategy_messages(prompt)  # Kullanıcı isteğini model mesajlarına dönüştürür.
        )  # Mesajları ortak istek akışına gönderip dönen metni iletir.

    async def repair_code(
        self,  # Metodun ait olduğu istemci nesnesidir.
        original_prompt: str,  # Kullanıcının başlangıçtaki isteğidir.
        current_code: str,  # Düzeltilmesi istenen mevcut koddur.
        context: RepairFailureContext,  # Önceki doğrulama veya çalışma hatasının bağlamıdır.
    ) -> str:  # Düzeltme isteğinden gelen metni döndürür.
        return await self._complete(
            build_repair_messages(
                original_prompt,  # Düzeltmede kullanıcı niyetini korumak için aktarılır.
                current_code,  # Modelin düzeltmesi gereken kod aktarılır.
                context,  # Modelin dikkate alacağı hata bağlamı aktarılır.
            )
        )  # Hazırlanan mesajları ilk üretimle aynı bağlantı akışından geçirir.

    async def _complete(self, messages: list) -> str:  # Ana model ve fallback akışını yönetir.
        if not self._managed:  # Dışarıdan async with kullanılmadıysa kendi bağlamını açar.
            async with self:  # __aenter__ çalışır ve _managed True olur.
                return await self._complete(messages)  # Bu kez bağlam açıkken aynı akışa girer.

        if self._client is None:  # İstemci daha önce oluşturulmamışsa oluşturur.
            self._open_client()  # Anahtarı kontrol eder ve API istemcisini hazırlar.

        primary = self._settings.nvidia_model  # Önce denenecek ana modelin adını alır.

        try:  # Ana model çağrısındaki kontrollü hataları yakalamaya hazırlanır.
            return await self._complete_model(messages, primary)  # Önce ana modeli çalıştırır.
        except NvidiaNimError as error:  # Kendi hata sınıfımızdan gelen hataları yakalar.
            fallback = self._settings.nvidia_fallback_model  # Yapılandırılmış yedek modeli alır.

            if (
                not fallback  # Yedek model tanımlı değilse fallback yapılamaz.
                or fallback == primary  # Yedek ana modelle aynıysa fallback yapılmaz.
                or error.kind not in (
                    ProviderErrorKind.MODEL_UNAVAILABLE,  # Bu kategori fallback'e uygundur.
                    ProviderErrorKind.TIMEOUT,  # Zaman aşımı da fallback'e uygundur.
                )  # Diğer hata kategorileri fallback'e uygun değildir.
            ):
                raise  # Yakalanan hatayı değiştirmeden üst katmana iletir.

            logger.warning(
                "NVIDIA fallback selected primary=%s fallback=%s reason=%s",  # Log şablonudur.
                primary,  # Başarısız olan ana modelin adıdır.
                fallback,  # Denenecek yedek modelin adıdır.
                error.kind.value,  # Yedeğe geçiş nedeninin metin değeridir.
            )

            # Yedek model aynı mesajları alır; başarısız olursa başka fallback yapılmaz.
            return await self._complete_model(messages, fallback)  # Yedek modelin sonucunu döndürür.

    async def _complete_model(
        self,  # Çağrının ait olduğu istemci nesnesidir.
        messages: list,  # Seçilen modele gönderilecek mesajlardır.
        model: str,  # Bu çağrıda kullanılacak modelin adıdır.
    ) -> str:  # Bir modelin tüm denemelerini tek zaman bütçesiyle çalıştırır.
        started = perf_counter()  # Bu model akışının başlangıç zamanını kaydeder.

        # Bekleme sırasında süre dolarsa asıl hata kategorisini korumak için kullanılır.
        state: dict[str, ProviderErrorKind | None] = {
            "backoff_failure": None  # Başlangıçta yeniden deneme beklemesi yoktur.
        }

        try:  # Modelin toplam zaman bütçesinin aşılmasını yakalamaya hazırlanır.
            # Bu süre ağ denemelerini ve aradaki beklemeleri birlikte kapsar.
            # Bütçe model başınadır; fallback çağrısı kendi bütçesini yeniden açar.
            async with asyncio.timeout(
                self._settings.nvidia_request_timeout_seconds  # Model başına süre sınırıdır.
            ):
                return await self._attempts(
                    messages,  # Gönderilecek mesajları aktarır.
                    model,  # Kullanılacak modeli aktarır.
                    state,  # Bekleme nedeninin paylaşılacağı sözlüğü aktarır.
                )

        except TimeoutError as error:  # Dış zaman bütçesi aşıldığında bu kola girer.
            kind = state["backoff_failure"] or ProviderErrorKind.TIMEOUT  # Asıl kategori varsa korur.

            logger.error(
                "NVIDIA NIM request failed model=%s category=%s duration_seconds=%.3f",
                model,  # Süresi dolan modelin adını kaydeder.
                kind.value,  # Korunan veya yeni belirlenen hata kategorisini kaydeder.
                perf_counter() - started,  # Geçen toplam süreyi hesaplayıp kaydeder.
            )

            raise NvidiaNimError(
                "NVIDIA NIM isteği zaman aşımına uğradı.",  # Kontrollü hata mesajıdır.
                kind=kind,  # Bekleme sırasında oluşmuşsa önceki hata kategorisini korur.
            ) from error  # Orijinal hatayı neden zincirinde saklar.

    async def _attempts(
        self,  # İstemci nesnesidir.
        messages: list,  # API'ye gönderilecek mesajlardır.
        model: str,  # İstek yapılacak modeldir.
        state: dict[str, ProviderErrorKind | None],  # Bekleme nedenini üst metotla paylaşır.
    ) -> str:  # API çağrılarını ve aynı modele yeniden denemeleri yürütür.
        assert self._client is not None  # İstemcinin hazır olması gerektiğini kontrol eder.

        retryable = {
            ProviderErrorKind.TIMEOUT,  # Zaman aşımı olursa tekrar denenebilir.
            ProviderErrorKind.RATE_LIMIT,  # İstek sınırı hatası olursa tekrar denenebilir.
            ProviderErrorKind.SERVER,  # 5xx hatası olursa tekrar denenebilir.
        }  # Ağ, kimlik ve boş yanıt hataları bu tekrar listesinde değildir.

        for attempt in range(
            self._settings.nvidia_max_retries + 1  # İlk çağrıya ek olarak tekrar hakkını sayar.
        ):
            state["backoff_failure"] = None  # Yeni denemede önceki bekleme nedenini temizler.
            started = perf_counter()  # Bu tek denemenin başlangıç zamanını alır.

            logger.info(
                "NVIDIA NIM attempt started model=%s attempt=%s",  # Başlangıç logunun şablonudur.
                model,  # Denenen modelin adını yazar.
                attempt + 1,  # Sıfır tabanlı sayacı okunabilir deneme numarasına çevirir.
            )

            try:  # SDK kaynaklı API hatalarını yakalamaya hazırlanır.
                completion = await self._client.chat.completions.create(
                    model=model,  # Sağlayıcının kullanacağı modeli belirtir.
                    messages=messages,  # Sistem ve kullanıcı mesajlarını gönderir.
                    max_tokens=self._settings.nvidia_max_tokens,  # Çıktı token sınırını belirtir.
                    stream=False,  # Yanıtı parça parça değil, tamamlanmış olarak ister.
                    **get_model_options(model),  # Modele özel sözlüğü isimli argümanlara açar.
                )

            except OpenAIError as error:  # SDK'nın ürettiği hata nesnesini yakalar.
                details = get_provider_error_details(
                    error,  # Hata türü ve HTTP durumuna göre sınıflandırılacak nesnedir.
                    api_key=self._settings.nvidia_api_key.get_secret_value().strip(),
                )  # Anahtar, yalnız istek kimliğini filtrelemek için fonksiyona aktarılır.

                logger.error(
                    "NVIDIA NIM request failed model=%s attempt=%s duration_seconds=%.3f %s",
                    model,  # Hatanın hangi modelde oluştuğunu yazar.
                    attempt + 1,  # Hatanın kaçıncı denemede oluştuğunu yazar.
                    perf_counter() - started,  # Denemenin ne kadar sürdüğünü hesaplar.
                    details.as_text(),  # Kontrollü hata ayrıntılarını metne dönüştürür.
                )

                if (
                    details.kind in retryable  # Hata tekrar denemeye uygun olmalıdır.
                    and attempt < self._settings.nvidia_max_retries  # Tekrar hakkı kalmalıdır.
                ):
                    state["backoff_failure"] = details.kind  # Bekleme nedenini saklar.

                    await asyncio.sleep(
                        self._settings.nvidia_retry_backoff_seconds  # Sabit bekleme süresidir.
                    )  # Beklerken diğer asenkron görevlerin ilerlemesine izin verir.

                    continue  # Döngünün sonraki turunda aynı modele yeniden istek gönderir.

                raise NvidiaNimError(
                    "NVIDIA NIM isteği başarısız oldu.",  # Kontrollü hata açıklamasıdır.
                    kind=details.kind,  # Sınıflandırılmış hata kategorisini korur.
                ) from error  # SDK hatasını neden zincirinde saklayarak hatayı iletir.

            if not completion.choices:  # API yanıtında hiç seçenek bulunmuyorsa kontrol eder.
                logger.warning(
                    "NVIDIA NIM empty response model=%s attempt=%s duration_seconds=%.3f",
                    model,  # Boş yanıtı döndüren modeli kaydeder.
                    attempt + 1,  # Deneme numarasını kaydeder.
                    perf_counter() - started,  # Denemenin süresini kaydeder.
                )

                raise NvidiaNimError(
                    "NVIDIA NIM boş bir yanıt döndürdü.",  # Boş yanıt açıklamasıdır.
                    kind=ProviderErrorKind.INVALID_RESPONSE,  # Yanıtı geçersiz olarak sınıflandırır.
                )

            content = completion.choices[0].message.content  # İlk seçenekteki mesaj metnini alır.

            if not content or not content.strip():  # Metin yoksa veya yalnız boşluksa reddeder.
                logger.warning(
                    "NVIDIA NIM empty response model=%s attempt=%s duration_seconds=%.3f",
                    model,  # Kullanılamayan içeriği döndüren modeli kaydeder.
                    attempt + 1,  # Deneme numarasını kaydeder.
                    perf_counter() - started,  # Denemenin süresini kaydeder.
                )

                raise NvidiaNimError(
                    "NVIDIA NIM boş bir yanıt döndürdü.",  # Kontrollü hata açıklamasıdır.
                    kind=ProviderErrorKind.INVALID_RESPONSE,  # Geçersiz yanıt kategorisini seçer.
                )

            self._last_model = (
                getattr(completion, "model", None) or model  # Yanıttaki model yoksa isteneni kullanır.
            )

            logger.info(
                "NVIDIA NIM request succeeded requested_model=%s returned_model=%s "
                "attempt=%s duration_seconds=%.3f",  # Başarılı çağrı logunun şablonudur.
                model,  # İstekte talep edilen modelin adıdır.
                self._last_model,  # Yanıtta bildirilen veya alternatif olarak saklanan modeldir.
                attempt + 1,  # Başarının kaçıncı denemede geldiğini kaydeder.
                perf_counter() - started,  # Başarılı denemenin süresini kaydeder.
            )

            return content.strip()  # Yanıtın çevresindeki boşlukları temizleyip metni döndürür.

        # Normal ayarlarda her deneme ya sonuç döndürür ya da hata fırlatır.
        raise AssertionError("Unreachable retry state")  # Beklenmeyen döngü bitişini bildirir.