# LLM Trading Strategy Mobile

Kullanıcının doğal dilde tanımladığı trading stratejisini NVIDIA NIM üzerinden
LLM ile Python strateji koduna dönüştüren uçtan uca bir sistemdir. Üretilen kod
statik güvenlik kontrollerinden ve Docker sandbox doğrulamasından geçirilir;
BIST hisselerinin geçmiş verileri üzerinde backtest yapılır ve sonuçlar Flutter
tabanlı web/mobile arayüzünde gösterilir.

## Live Demo

[Open Live Strategy Lab](https://strategy-lab.denmarkeast.cloudapp.azure.com/)

Canlı demo, Azure VM üzerinde çalışan **Flutter Web + FastAPI** deploymentıdır.
Nginx, HTTPS bağlantılarını karşılar, Flutter Web dosyalarını sunar ve API
isteklerini yalnızca localhost üzerinde dinleyen FastAPI servisine yönlendirir.

## Architecture

```text
Flutter Web / Mobile
        ↓
FastAPI
        ↓
NVIDIA NIM
        ↓
Generated Python Strategy
        ↓
AST Validation
        ↓
Bounded Repair (doğrulama veya smoke testi başarısız olursa)
        ↓
Docker Sandbox Smoke Test
        ↓
Strategy Freeze (SHA-256)
        ↓
Yahoo Finance BIST Data
        ↓
Held-Out Backtest (Docker sandbox)
        ↓
Metrics → Flutter arayüzü
```

Onarım zorunlu bir adım değildir: statik doğrulama veya deterministik smoke
testi başarısız olursa sınırlı sayıda yeniden üretim yapılır ve yeni sürüm tekrar
doğrulanır. Varsayılan sınır, ilk üretim dahil üç strateji sürümüdür. Smoke testi
başarılı olduğunda kod SHA-256 ile sabitlenir; son altı takvim ayına ayrılmış
held-out test verisi veya backtest sonuçları onarım amacıyla LLM'e gönderilmez.

**Güvenlik:** LLM tarafından oluşturulan Python kodu FastAPI host process içinde
doğrudan çalıştırılmaz. Generated strategy yalnızca statik doğrulama sonrasında
izole Docker sandbox ortamında çalıştırılır. Sandbox ağ erişimi kapalı,
salt okunur kök dosya sistemine sahip, ayrıcalıksız kullanıcıyla çalışan ve
süre/CPU/bellek/process sınırları uygulanan bir ortamdır. AST ve lookahead
kontrolleri güvenlik katmanlarıdır; stratejinin doğruluğunu veya kârlılığını
garanti etmez.

## Tech Stack

| Katman | Teknolojiler |
| --- | --- |
| Backend | Python, FastAPI |
| Arayüz | Flutter, Dart |
| Strateji üretimi | NVIDIA NIM |
| İzole çalışma ortamı | Docker |
| Veri ve backtest | Yahoo Finance (`yfinance`), backtesting.py, pandas, NumPy |
| Deployment ve kaynak yönetimi | Nginx, Azure VM, GitHub |

## Features

- Doğal dilden Python strateji üretimi.
- SMA, EMA, RSI, MACD, Bollinger Bands, Stochastic ve ATR indikatör desteği.
- BIST sembolleri ve Yahoo Finance için `.IS` sembol dönüşümü.
- AST tabanlı statik doğrulama ve lookahead kontrolleri.
- Sınırlı onarım (bounded repair) ve Docker sandbox smoke testi.
- SHA-256 strategy freeze ve çalışma sonucunda bütünlük kontrolü.
- Tamamlanmış günlük verilerle held-out backtesting.
- Başlangıç sermayesi ve komisyon ayarları.
- Getiri, net kâr/zarar, işlem sayısı, win rate, drawdown, Sharpe, Sortino ve
  diğer backtest metriklerinin gösterimi.
- Flutter mobile/web arayüzü ve herkese açık Azure demosu.

Desteklenen semboller: `THYAO`, `ASELS`, `TUPRS`, `BIMAS`, `EREGL`, `KCHOL`,
`GARAN`, `AKBNK`, `SISE`, `SAHOL`, `FROTO`, `TOASO`.

## API

| Method | Endpoint | Açıklama |
| --- | --- | --- |
| GET | `/health` | Uygulama sağlık kontrolü; `{"status":"ok"}` döndürür. |
| GET | `/api/v1/strategy-lab/capabilities` | Desteklenen semboller, indikatörler, varsayılanlar ve prompt sınırları. |
| POST | `/api/v1/strategy-lab/run` | Üretim, doğrulama, sandbox ve backtest akışını çalıştırır. |
| POST | `/api/v1/strategies/generate` | Doğal dilden strateji kodu üretir. |
| POST | `/api/v1/strategies/validate` | Kaynak kodunu çalıştırmadan statik olarak doğrular. |
| POST | `/api/v1/backtests/bist` | Repoya ait güvenilir referans SMA stratejisiyle BIST backtest yapar. |

Strategy Lab örnek isteği:

```json
{
  "prompt": "RSI 35 altında al ve RSI 70 üzerinde sat.",
  "symbol": "THYAO",
  "initial_cash": 100000,
  "commission": 0.002
}
```

`prompt`, baştaki/sondaki boşluklar temizlendikten sonra 5–2000 karakter
olmalıdır. `symbol` zorunludur ve desteklenen BIST sembollerinden biri olmalıdır.
`initial_cash` sıfırdan büyük olmalıdır; varsayılanı `100000` değeridir.
`commission`, `0 <= commission < 0.1` aralığında bir orandır; varsayılan
`0.002`, %0,2 komisyona karşılık gelir.

Başarılı yanıt üretilen kodu, deneme sayısını, doğrulama/runtime bilgilerini,
veri dönemini, backtest ayarlarını ve metrikleri içerir. İşlem tek HTTP isteği
içinde tamamlanır ve LLM/veri servislerine bağlı olarak zaman alabilir.
Yerel backend'in OpenAPI arayüzü: `http://127.0.0.1:8000/docs`.

## Running Locally

Gereksinimler: Python 3.11+, Flutter 3.35.x / Dart 3.9.2 ile uyumlu SDK,
çalışan Docker daemon ve strateji üretimi için NVIDIA NIM API anahtarı.
Aşağıdaki komutlar Windows PowerShell içindir; her komut bloğuna belirtilen
dizinden başlayın.

### Backend

Repo kökünden, ilk kurulumda:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

`backend/.env` içindeki `NVIDIA_API_KEY` değerini kendi ortamınızda doldurun.
Gerçek anahtarları, `.env` dosyalarını veya SSH bilgilerini repoya eklemeyin.

`backend/` dizininde, sanal ortam aktif ve Docker daemon çalışırken sandbox
image'ini oluşturup doğrulayın:

```powershell
docker build -f sandbox/Dockerfile -t llm-strategy-sandbox:dev sandbox
python scripts/check_sandbox.py
```

Aynı dizinde backend'i başlatın:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Sağlık kontrolü: `http://127.0.0.1:8000/health`.

### Flutter

Repo kökünden yeni bir terminalde:

```powershell
cd mobile
flutter pub get
flutter run
```

Yerel geliştirmede Android emülatörü varsayılan olarak `http://10.0.2.2:8000`,
diğer native platformlar `http://127.0.0.1:8000` adresini kullanır. Fiziksel
cihazlar için erişilebilir bir backend adresi gerekir. Native hedeflerde adres
`--dart-define=API_BASE_URL=...` ile değiştirilebilir.

Web sürümü `/api/` isteklerini **aynı origin** üzerinden gönderir ve
`API_BASE_URL` tanımını kullanmaz. Yerel web kullanımı için
`flutter build web --release` çıktısı, `/api/` isteklerini FastAPI'ye ileten
bir web sunucusuyla sunulmalıdır; yalnızca Flutter geliştirme sunucusunu açmak
API proxy'si sağlamaz. [Nginx şablonu](deploy/azure/nginx.conf) bu yönlendirmeyi
gösterir; yerel kullanımda web root yolunu yerel build dizinine uyarlayın.

### Tests and Build

`backend/` dizininde, sanal ortam aktifken:

```powershell
python -m pytest
```

Backend testleri gerçek NVIDIA API anahtarı, Yahoo Finance veya dış ağ gerektirmez.
Docker image kontrolü yukarıdaki `check_sandbox.py` komutuyla ayrıca yapılır.

`mobile/` dizininde:

```powershell
flutter analyze
flutter test
flutter build web --release
```

Web çıktısı `mobile/build/web/` altında oluşur ve Git'e eklenmez.

## Deployment

```text
Browser → HTTPS → Azure VM / Nginx → Flutter Web
                             └── /api/... → FastAPI (127.0.0.1:8000)
                             └── /health  → FastAPI (127.0.0.1:8000)
```

Azure'daki repo `/opt/llm-trading-strategy-mobile`, backend çalışma dizini
`/opt/llm-trading-strategy-mobile/backend`, Flutter Web sunum dizini
`/var/www/strategy-lab` konumundadır. FastAPI, `llm-strategy` systemd servisi
olarak çalışır. **FastAPI internete doğrudan 8000 portundan açılmaz**;
Nginx `/api/` önekini koruyarak localhost backend'e proxy yapar.

Repodaki [deploy/azure/nginx.conf](deploy/azure/nginx.conf), HTTP için başlangıç
şablonudur. Canlı ortam ayrıca demo alan adına bağlı HTTPS ve Certbot tarafından
yönetilen TLS yapılandırmasını kullanır. Şablon, canlı HTTPS yapılandırmasının
birebir kopyası değildir ve aktif yapılandırmanın üzerine doğrudan yazılmamalıdır.
Sertifikalar, özel anahtarlar ve ortama özgü gizli değerler Git dışında tutulur.

Web deploymentında yalnızca release build'in `build/web/` içeriği web root'a
sunulur. Backend ortam dosyaları, SSH anahtarları, QA çıktıları ve loglar public
web dizinine veya GitHub'a taşınmaz.

## Disclaimer

Backtest sonuçları geçmiş piyasa verilerine dayanır ve gelecekteki performansı
garanti etmez. Sistem eğitim ve araştırma amaçlıdır; yatırım tavsiyesi vermez
ve gerçek emir göndermez. Yahoo Finance verisinin kesintisiz veya gerçek zamanlı
olduğu garanti edilmez. `yfinance`, Yahoo tarafından desteklenen resmî bir
istemci değildir; veri kullanımında ilgili sağlayıcının koşulları dikkate
alınmalıdır.

## Project Structure and Further Reading

```text
backend/       FastAPI, LLM, doğrulama, veri, backtest ve Docker sandbox
mobile/        Flutter mobile/web uygulaması
deploy/azure/  Nginx deployment şablonu
docs/          Mimari ve teknik dokümantasyon
```

- [Backend kurulumu ve API ayrıntıları](backend/README.md)
- [Flutter API yapılandırması](mobile/README.md)
- [Mimari](docs/architecture.md)
- [AST doğrulaması](docs/ast-validation.md)
- [BIST backtest](docs/day4-bist-backtest.md)
- [Güvenli runtime ve Strategy Lab](docs/day5-safe-runtime-and-strategy-lab.md)
