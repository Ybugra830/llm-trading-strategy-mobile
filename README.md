# LLM Trading Strategy Mobile

LLM Trading Strategy Mobile, doğal dilde tanımlanan teknik analiz stratejilerini
Python koduna dönüştürmek ve ilerleyen aşamalarda doğrulayıp geçmiş piyasa
verileri üzerinde test etmek amacıyla geliştirilen mobil uygulama ve backend
projesidir.

> **Mevcut durum:** Backend, NVIDIA NIM üzerinden ilk strateji kodu üretim
> endpoint'ini sunar. Üretilen kod henüz doğrulanmaz, çalıştırılmaz veya backtest
> edilmez. Flutter uygulaması halen başlangıç kabuğu aşamasındadır.

## Depo yapısı

```text
backend/  FastAPI uygulaması, NVIDIA NIM entegrasyonu ve backend testleri
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

Swagger'da strateji üretim endpoint'ini açıp **Try it out** seçeneğiyle doğal
dilde bir strateji isteği gönderebilirsiniz.

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

Bu aşamada LLM çıktısı yalnızca metin olarak döndürülür. AST doğrulaması, güvenli
kod çalıştırma, `ta`, `backtesting.py`, `yfinance`, piyasa verisi ve backtest
henüz uygulanmamıştır. Docker, Nginx ve VPS dağıtımı da sonraki aşamalardadır.

Ayrıntılı backend kullanımı için [backend/README.md](backend/README.md), hedef
mimari için [docs/architecture.md](docs/architecture.md) dosyasına bakın.
