# LLM Trading Strategy Mobile

LLM destekli teknik analiz stratejilerinin üretilmesi, doğrulanması ve
backtest edilmesi için geliştirilecek mobil uygulama ve backend projesidir.

Bu ilk sürüm yalnızca çalıştırılabilir proje iskeletini içerir. Azure OpenAI,
piyasa verisi, teknik analiz, strateji üretimi ve backtest iş mantığı sonraki
aşamalarda eklenecektir.

## Teknolojiler

- Mobile: Flutter (Android ve iOS)
- Backend: Python 3.11+ ve FastAPI
- Planlanan entegrasyonlar: Azure OpenAI, `ta`, `backtesting.py`, `yfinance`
- Test: pytest ve Flutter test araçları
- Planlanan dağıtım: Docker, Nginx ve Ubuntu VPS

## Proje yapısı

```text
backend/  FastAPI uygulaması ve backend testleri
mobile/   Flutter mobil uygulaması
docs/     Mimari ve staj süreci dokümantasyonu
```

## Backend kurulumu

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Sağlık kontrolü `http://127.0.0.1:8000/health` adresinden erişilebilir.

Backend testlerini çalıştırmak için:

```powershell
cd backend
pytest
```

## Mobile kurulumu

Flutter 3.35.5 veya uyumlu bir sürüm gereklidir.

```powershell
cd mobile
flutter pub get
flutter run
```

Mobile doğrulamalarını çalıştırmak için:

```powershell
cd mobile
flutter analyze
flutter test
```

## Güvenlik ve depo temizliği

API anahtarları, gerçek `.env` dosyaları, IDE ayarları, önbellekler ve build
çıktıları Git'e eklenmez. İleride ortam değişkenleri gerektiğinde yalnızca
örnek ve secrets içermeyen `.env.example` dosyaları paylaşılacaktır.

Mimari hedefler için [docs/architecture.md](docs/architecture.md), geliştirme
aşamaları için [docs/internship-plan.md](docs/internship-plan.md) dosyasına
bakın.
