# Sistem Mimarisi

## Mevcut uygulama

Projenin mevcut aşamasında aşağıdaki parçalar vardır:

- Android ve iOS hedefli Flutter uygulama kabuğu
- FastAPI backend uygulaması
- `GET /health` sağlık endpoint'i
- `POST /api/v1/strategies/generate` NVIDIA NIM kod üretim endpoint'i
- `POST /api/v1/strategies/validate` AST tabanlı statik doğrulama endpoint'i
- Ağdan bağımsız backend testleri ve Türkçe dokümantasyon

Mobil uygulama henüz backend'e bağlanmaz. Piyasa verisi, teknik indikatör
hesaplama, kod çalıştırma ve backtest işlevleri yoktur.

## Mevcut kod üretim ve doğrulama akışı

```text
Doğal dil strateji isteği
        ↓
FastAPI /generate
        ↓
NVIDIA NIM
        ↓
Python kaynak kodu (güvenilmeyen metin)
        ↓
FastAPI /validate
        ↓
Kod temizleme
        ↓
ast.parse()
        ↓
Import + güvenlik + interface + basit look-ahead kontrolleri
        ↓
ValidationResponse
```

Doğrulama endpoint'i üretim endpoint'ini otomatik çağırmaz. İstemci, üretilen
metni ayrı bir istekle doğrulamaya gönderir. Bu ayrım mevcut iki adımı açık ve
bağımsız tutar.

## Statik doğrulama güvenlik sınırı

`ast.parse()` kaynak kodunu bir Abstract Syntax Tree'ye dönüştürür ve normal
Python ifadelerini çalıştırmaz. Sistem, izin verilen import köklerini, belirli
yasaklı çağrıları, `GeneratedStrategy` arayüzünü ve açık negatif `.shift(-N)`
kalıplarını kontrol eder.

LLM çıktısı güvenilir uygulama kodu değildir. AST doğrulaması yalnızca bilinen
bazı riskleri tespit eder; alias çözümü, kapsamlı veri akışı analizi veya eksiksiz
look-ahead tespiti yapmaz ve tam bir sandbox değildir. Bu aşamada üretilen kod
çalıştırılmamaktadır.

## Planlanan mimari

```text
Flutter Mobile
      ↓ HTTPS
FastAPI Backend
      ↓
LLM Provider (mevcut: NVIDIA NIM)
      ↓
Statik ve sonraki aşamalarda genişletilecek strateji doğrulaması
      ↓
Piyasa verisi
      ↓
İzole backtest
      ↓
Sonuçların Flutter'a döndürülmesi
```

`yfinance`, `ta`, `backtesting.py`, güvenli yürütme ortamı, Docker, Nginx ve VPS
dağıtımı yalnızca planlanmaktadır; bu aşamada runtime bağımlılığı veya çalışan iş
mantığı olarak eklenmemiştir.

## Güvenlik ilkeleri

- Gizli değerler yalnızca sunucu tarafındaki ortam değişkenlerinde tutulur.
- Gerçek `.env` dosyaları ve API anahtarları Git'e eklenmez.
- Sağlayıcı hata ayrıntıları public API yanıtlarına taşınmaz.
- LLM çıktısı hiçbir zaman doğrudan çalıştırılabilir veya güvenilir kabul edilmez.
- Gelecekteki yürütme aşaması, statik doğrulamadan ayrı bir izolasyon katmanı
  gerektirir.
