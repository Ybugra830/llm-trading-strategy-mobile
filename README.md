# LLM Trading Strategy Mobile

LLM Trading Strategy Mobile, doğal dilde tanımlanan teknik analiz stratejilerini
Python koduna dönüştürmek ve ilerleyen aşamalarda doğrulayıp geçmiş piyasa
verileri üzerinde test etmek amacıyla geliştirilen mobil uygulama ve backend
projesidir.

> **Mevcut durum:** Backend, NVIDIA NIM üzerinden strateji kodu üretim endpoint'i
> ve AST tabanlı statik doğrulama endpoint'i sunar. Üretilen kod hiçbir aşamada
> çalıştırılmaz veya backtest edilmez. Flutter uygulaması halen başlangıç kabuğu
> aşamasındadır.

## Depo yapısı

```text
backend/  FastAPI, NVIDIA NIM, statik doğrulama ve backend testleri
mobile/   Android ve iOS hedefli Flutter uygulama iskeleti
docs/     Türkçe mimari ve staj dokümantasyonu
```

## Backend kurulumu

Python 3.11 veya daha yeni bir sürüm gereklidir.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Oluşturulan `.env` dosyasında `NVIDIA_API_KEY` değerini yerel olarak doldurun.
Gerçek API anahtarlarını veya `.env` dosyasını Git'e eklemeyin.

## Backend'i çalıştırma

```powershell
cd backend
uvicorn app.main:app --reload
```

- Sağlık kontrolü: `http://127.0.0.1:8000/health`
- Swagger arayüzü: `http://127.0.0.1:8000/docs`
- Strateji üretimi: `POST /api/v1/strategies/generate`
- Statik doğrulama: `POST /api/v1/strategies/validate`

Swagger'da üretim ve doğrulama endpoint'lerini **Try it out** seçeneğiyle
deneyebilirsiniz. Güvensiz veya geçersiz kaynak kodu normal sonuç olarak HTTP
200 ve `valid=false` döndürür; boş ya da 20.000 karakterden uzun `code` alanı
HTTP 422 döndürür.

## Backend testleri

```powershell
cd backend
pytest
```

Backend testleri gerçek NVIDIA API anahtarı veya dış ağ kullanmaz.

## Flutter kurulumu ve çalıştırma

Flutter 3.35.x gereklidir.

```powershell
cd mobile
flutter pub get
flutter run
```

## Flutter analizi ve testleri

```powershell
cd mobile
flutter analyze
flutter test
```

## Mevcut sınırlar ve sonraki aşamalar

LLM çıktısı güvenilir uygulama kodu değildir. Mevcut AST doğrulaması riski azaltan
statik bir filtredir; tam bir sandbox değildir. Bu aşamada üretilen kod
çalıştırılmamaktadır. Güvenli kod çalıştırma, `ta`, `backtesting.py`, `yfinance`,
piyasa verisi ve backtest henüz uygulanmamıştır. Docker, Nginx ve VPS dağıtımı da
sonraki aşamalardadır.

Ayrıntılı backend kullanımı için [backend/README.md](backend/README.md), hedef
mimari için [docs/architecture.md](docs/architecture.md), AST teknik notu için
[docs/ast-validation.md](docs/ast-validation.md) dosyasına bakın.
