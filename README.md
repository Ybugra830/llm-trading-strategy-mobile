# LLM Trading Strategy Mobile

LLM Trading Strategy Mobile, doğal dilde tanımlanan teknik analiz stratejilerini
Python koduna dönüştürmek ve ilerleyen aşamalarda doğrulayıp geçmiş piyasa
verileri üzerinde test etmek amacıyla geliştirilen mobil uygulama ve backend
projesidir.

> **Mevcut durum:** Backend; NVIDIA NIM strateji üretimi, AST tabanlı statik
> doğrulama ve tamamlanmış günlük BIST verisinde güvenilir referans stratejiyle
> backtest endpoint'leri sunar. LLM tarafından üretilen kod çalıştırılmaz veya
> Day 4 backtest motoruna bağlanmaz. Flutter uygulaması halen başlangıç kabuğu
> aşamasındadır.

## Depo yapısı

```text
backend/  FastAPI, NVIDIA NIM, statik doğrulama, BIST verisi ve backtest
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
- BIST backtest: `POST /api/v1/backtests/bist`

Swagger'da üretim ve doğrulama endpoint'lerini **Try it out** seçeneğiyle
deneyebilirsiniz. Güvensiz veya geçersiz kaynak kodu normal sonuç olarak HTTP
200 ve `valid=false` döndürür; boş ya da 20.000 karakterden uzun `code` alanı
HTTP 422 döndürür.

## BIST backtest

Day 4 endpoint'i yalnızca `THYAO`, `ASELS`, `TUPRS`, `BIMAS`, `EREGL`,
`KCHOL`, `GARAN`, `AKBNK`, `SISE`, `SAHOL`, `FROTO` ve `TOASO`
sembollerini kabul eder. Sembol Yahoo Finance için `.IS` ekiyle dönüştürülür.

Yaklaşık üç yıllık düzeltilmiş günlük OHLCV indirilir. Bugün exclusive bitiş
tarihi olduğundan potansiyel olarak tamamlanmamış güncel bar backtest'e girmez.
Temiz verinin son altı takvim ayı görülmemiş test dönemi olarak ayrılır ve
repository-owned `ReferenceSmaCrossStrategy` yalnızca bu dönemde çalıştırılır.

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/backtests/bist `
  -ContentType "application/json" `
  -Body '{"symbol":"THYAO","initial_cash":100000,"commission":0.002}'
```

Yanıt; gerçek veri ve test tarihlerini, satır sayılarını, backtest ayarlarını,
getiri, buy-and-hold, net kâr/zarar, işlem sayısı, win rate, drawdown, Sharpe,
Sortino, Profit Factor, işlem ve exposure metriklerini içerir.

## Backend testleri

```powershell
cd backend
pytest
```

Backend testleri gerçek NVIDIA API anahtarı, Yahoo Finance veya dış ağ kullanmaz.

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
statik bir filtredir; tam bir sandbox değildir. Day 4, piyasa verisi ve backtest
altyapısını yalnızca güvenilir repository-owned kodla doğrular. Üretilen LLM
kodu çalıştırılmamaktadır. Runtime/sandbox köprüsü, indikatör referans
karşılaştırması, Flutter API entegrasyonu ve deployment sonraki aşamalardadır.

Yahoo Finance verisi için gerçek zaman veya kesintisiz erişim garantisi yoktur.
`yfinance`, Yahoo tarafından desteklenen resmî bir istemci değildir ve kullanım
eğitim/araştırma amacıyla Yahoo koşullarına uygun olmalıdır. Sistem yatırım
tavsiyesi vermez, gerçek emir göndermez ve geçmiş performans gelecekteki sonucu
garanti etmez.

Ayrıntılı backend kullanımı için [backend/README.md](backend/README.md), hedef
mimari için [docs/architecture.md](docs/architecture.md), AST teknik notu için
[docs/ast-validation.md](docs/ast-validation.md), Day 4 açıklaması için
[docs/day4-bist-backtest.md](docs/day4-bist-backtest.md) dosyasına bakın.
