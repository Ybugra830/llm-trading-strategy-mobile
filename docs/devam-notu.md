# Strategy Lab — devam notu

Duraklatma tarihi: 24 Ekim 2026 (Europe/Istanbul).
Çalışılan depo: `C:\Users\Erbay\Desktop\llm-trading-strategy-mobile\llm-trading-strategy-mobile` (iç depo).
Dal: `codex/strategy-lab-release`. Bu turun başlangıç commit'i: `648d3aa728849eadb19141321c357ce711568fe7`.
Bu not ve uygulama değişiklikleri aynı devam commit'ine alınır; commit kimliği `git log -1` ile bulunur. Main'e merge ve force push yapılmaz.

## Kesin durum ve devam kararı

- Primary, `nvidia/nemotron-3-super-120b-a12b` olarak ayarlı. Çalışan fallback bulunamadı; etkin fallback yok.
- Güncel yerel model bağlantısı çalışmıyor; sürüm canlıya hazır değil. Katalogda görünmek üretim yapabildiğini kanıtlamaz. Aşağıdaki HTTP sonuçları modelin her hesapta veya endpoint'te tamamen kaldırıldığı anlamına gelmez.
- Gerçek RSI uçtan uca akışı, gerçek repair ve RSI işlemleri/portföyünün bağımsız hesabı bu tur doğrulanmadı. Başarılı model çıktısı, yeni piyasa verisi veya Nemotron backtest sonucu yok.
- Makale ve geçmiş GPT-OSS/Llama deneyleri değiştirilmedi. Mistral Nemotron geçmişte yalnız karşılaştırılmış ve 15 denemede başarısız olmuş adaydır; geçmişte çalışan yedek olarak sunulmamalı.
- Azure'daki eski canlı sürüme bu tur dokunulmadı. Yeni frontend canlıya aktarılmadı. Bu duraklatma işleminde model isteği, yeni test veya deploy yapılmadı.
- Devam edince ilk adım: eski çalışan istemci/ayarlarla güncel bağlantıyı karşılaştırıp Nemotron erişimini doğrulamak. Sırları veya ham hata gövdelerini yazdırma. Kullanıcı seçmeden başka model/sağlayıcıya veya ücretli hizmete geçme.

## Yapılan uygulama değişiklikleri

- `backend/app/config.py` ve `backend/.env.example`: varsayılan primary Nemotron oldu. Git dışında tutulan yerel `backend/.env` de primary için güncellendi; diğer env değerlerinin değişmediği önceki kontrolde doğrulandı. Gerçek env commit'e alınmaz.
- `backend/app/llm/nvidia_options.py`: Nemotron için temperature=1, top_p=0.95 ve `chat_template_kwargs.enable_thinking=false`; Mistral Nemotron için temperature=0.6, top_p=0.7 profilleri eklendi. GPT-OSS'ye özgü reasoning parametreleri bu modellere taşınmıyor. Profil bulunması modelin etkin olduğu veya çalıştığı anlamına gelmez.
- `backend/app/llm/nvidia_client.py`: uygunluk, üretim ve repair ortak çağrı politikasından geçer. Uygunluk toplam en fazla 30 saniye, her üretim/repair en fazla yapılandırılan 180 saniyedir. Primary en fazla yarısını (15/90 saniye), varsa fallback ilk son tarihe kadar kalanı kullanır. Erken primary hatasından kalan süre fallback'e kalır; retry ve beklemeler aynı bütçededir. Etkin fallback yokken primary yarım bütçede sonlanır.
- Geçiş yalnız timeout veya model/rota bulunamaması kategorilerindedir. Geçerli rejected/needs_clarification kararı, kimlik/izin/parametre hataları veya bozuk çıktı için fallback çağrılmaz. Üçüncü model ya da primary'ye dönen döngü yoktur. Sağlayıcı hatası kabul kararına dönüşmez.
- İstek kapsamındaki `attempt_records`, aşama, istenen/dönen model, ayarlar, zaman, güvenli hata kategorisi ve varsa içerik bilgisini tutar; istemler/çıktılar olağan loglara yazdırılmaz. Sağlayıcı model adı döndürmezse audit alanı boş kalır; eski `.model` alanı tek başına dönen model kanıtı değildir.
- `backend/tests/test_model_failover.py`, `test_nvidia_client.py`, `test_strategy_admission.py`: üç aşamada geçiş, ortak süre/retry/bekleme bütçeleri, erken hata, geçerli ret ve iki modelin başarısızlığı kontrolleri güncellendi. Sağlayıcı ve uygunluk belgeleri de güncellendi.
- Uygunluk kapısı, açıklama isteme, AST/Docker güvenliği, hesaplama düzeltmeleri ve Türkçe arayüz korunuyor. Bu tur frontend veya sandbox kaynakları değiştirilmedi.

## Gerçek doğrudan tanılar — bütün denemeler

Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`. Her modele tek istek, 30 saniye sınır, 512 token, stream=false, SDK retry=0. İstem: `Reply exactly OK.` Hiçbirinde kullanılabilir yanıt veya dönen model adı alınmadı.

| Kayıt / başlangıç (UTC, 24 Ekim 2026) | İstenen model | HTTP | Süre | Çağrı ayarı |
| --- | --- | --- | --- | --- |
| direct-01 / 06:59:10.226196 | nvidia/nemotron-3-super-120b-a12b | 404 | 4.351 sn | temperature=1, top_p=0.95, enable_thinking=false |
| direct-02 / 06:59:14.578430 | mistralai/mistral-nemotron | 410 | 0.653 sn | temperature=0.6, top_p=0.7 |
| direct-03 / 07:03:14.656923 | microsoft/phi-4-mini-instruct | 410 | 2.706 sn | temperature=0.1 |

Güvenli hata türü üçünde de `model_unavailable`. Mistral ve kullanıcı onayıyla test edilen Phi-4 Mini etkinleştirilmedi. Alternatif model seçimi için kullanıcı kararı gerekir.

## Gerçekten geçen kontroller ve sınırları

- Backend yerel/taklit regresyonu: **755 passed, 1 skipped**, 6.77 saniye; gerçek sağlayıcı çağrısı yok. Atlanan test opt-in Docker testiydi.
- Ayrı gerçek yerel Docker regresyonu: **1 passed**, 11.06 saniye. Mevcut dondurulmuş terminal emir örneğini çalıştırır; model çağrısı ve yeni piyasa verisi indirmesi yok. Nemotron RSI doğrulaması değildir.
- Yerel image: `llm-strategy-sandbox:dev`; ID: `sha256:7713f75ff8f2adc3bcc9ad464379402bd16b39cab7cf16fc88afe7eb6cb74cba`.
- Yerel ve image içindeki worker SHA-256 eşleşti: `8ce7d37783d41199087d2482081da386e71fd165c45e47833d25ec4377a94e5c`.
- Test kaydındaki çalışma ağacı kaynak özeti: `3394fc72fd36e9bd991fe8226ac5186a3ac19018e3fb3917932d0f8b1ccc63ef`; temel commit 648d3aa, kaynak o sırada değiştirilmişti. Testleri sonradan oluşacak commit üzerinde tekrar çalışmış gibi sunma.
- `asdfghjkl`, `bana kek tarifi ver`, `RSI` ve tam RSI14/30/70 için gerçek uygulama çağrıları erişim engeli nedeniyle çalıştırılmadı. Taklit testler bu gerçek senaryoların geçtiği anlamına gelmez.
- Flutter production build bu tur yeniden çalıştırılmadı; önceki release sonuçları yeni model bağlantısının kanıtı değildir.

### Yerel doğrulama komutları (devam için; duraklatırken çalıştırılmadı)

İç deponun `backend` klasöründen:

```powershell
.\.venv\Scripts\python.exe -B -m pytest -o addopts='' -q --tb=short -p no:cacheprovider
$env:RUN_CALCULATION_DOCKER_TESTS='1'
try {
    .\.venv\Scripts\python.exe -B -m pytest -o addopts='' -q --tb=short -p no:cacheprovider tests/test_terminal_order_regression.py::test_terminal_buy_cannot_open_without_a_future_bar
} finally {
    Remove-Item Env:RUN_CALCULATION_DOCKER_TESTS -ErrorAction SilentlyContinue
}
```

Settings önceliği: çağıranın açık Settings değerleri, OS ortamı, `backend/.env`, kök `.env`, varsayılanlar. Settings süreçte önbelleklenir; değişiklik sonrası backend yeniden başlatılmalıdır. Etkin ayar incelemesinde anahtar değerlerini yazdırma ve yerel env'i Azure'a kopyalama.

## Kanıtlar ve Git dışında bırakılanlar

İç depoya göre yerel kanıt kökü: `backend/verification/nemotron/20261024-065909Z/`. Bu küçük sonuç özeti Git'tedir; ham deney klasörü ve büyük arşivler Git'e alınmaz. Başka makinede devam için bu yerel klasör ayrıca gerekir.

- `direct-01.json`, `direct-02.json`, `direct-03.json`: yukarıdaki üç tanı isteğinin tüm ayarları ve güvenli hata sonuçları.
- `baslangic.json`, `son_durum.json`: temel commit, kaynak özeti, önce/sonra güvenli ayarlar; son_durum içindeki commit/push yapılmadı alanı kayıt oluşturulduğu ana aittir, bu duraklatma commit'inden öncedir.
- `taklit_testler.json`, `docker_regresyonu.json`: test sayıları, süreleri ve image/worker kimliği.
- `uygulama_senaryolari.json`, `sonuclar.csv`: çalıştırılmayan gerçek uygulama senaryoları dahil sonuçlar.
- `README.md`, `yontem_ve_sinirliliklar.md`, `resmi_kaynaklar.json`: yöntem, sınırlılıklar ve kullanılan belge bağlantıları.
- `uygulama_degisiklikleri.patch`, `envanter.csv`: o andaki kaynak farkı ve dosya SHA-256 envanteri; sonraki devam notu bu tarihsel envantere dahil değildir.

Depo dışındaki kullanıcıya özel ACL'li yerel yedek: `C:\Users\Erbay\.codex\private-backups\strategy-lab\20261024-065909Z`. İçeriği Git'e alınmaz veya terminale yazdırılmaz. Gerçek `backend/.env`, sanal ortamlar, build dosyaları, kimlik doğrulama dosyaları ve sır içeren loglar dışarıda kalır. Önceden mevcut makale arşivleri, doğrulama belgeleri ve yardımcı scriptler korunur; bu turun commit'ine eklenmez.

## Azure — yalnız önceden bilinen bilgiler, bu tur yeniden kontrol edilmedi

| Bileşen | Son bilinen konum / bilgi |
| --- | --- |
| Canlı adres | https://strategy-lab.denmarkeast.cloudapp.azure.com/ |
| Eski canlı depo / commit | `/opt/llm-trading-strategy-mobile` / kullanıcı tarafından bildirilen `c0ed5ac` |
| Eski canlı backend | `llm-strategy.service`, kullanıcı `azureuser`, port 8000; çalışma klasörü `backend`, env `backend/.env` |
| Önceden hazırlanan aday release | `/opt/strategy-lab-releases/648d3aa` |
| Önceden hazırlanan aday servis | `llm-strategy-candidate.service`, port 8001; son bildirilen ayarı GPT-OSS |
| Sandbox image etiketi | `llm-strategy-sandbox:dev`; Azure image ID/worker eşleşmesi bu tur doğrulanmadı; yerel ID'yi Azure ID'si sayma |
| Nginx frontend dizini | `/var/www/strategy-lab` |
| Önceden hazırlanan Azure yedeği | Kesin konumu kayıtlarda bulunamadı; yeniden salt okunur belirlenmeli. Yerel özel ayar yedeğiyle karıştırma. |

Sunucu durumları güncel doğrulanmadı. Azure işlemlerini kullanıcı RunShellScript üzerinden manuel yapacak. Yerel erişim ve uygulama zinciri başarıyla doğrulanmadan sunucu adımı yok. Sonrasında önce 8001 aday, image/worker ve yedek salt okunur kontrol edilmeli; çıktılar görülerek birer adım ilerlenmeli. Aday doğrulanmadan 8000 canlı servis veya frontend değiştirilmemeli. Geri dönüş komutları gerçek sunucu durumu/yedek konumu belirlendikten sonra kesinleştirilmeli.

**Model erişimi çözülmedi; canlıya alınmadı.**
