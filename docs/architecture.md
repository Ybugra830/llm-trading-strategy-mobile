# Sistem Mimarisi

## Mevcut uygulama

Projenin mevcut aşamasında aşağıdaki parçalar vardır:

- Android ve iOS hedefli Flutter uygulama kabuğu
- FastAPI backend uygulaması
- `GET /health` sağlık endpoint'i
- `POST /api/v1/strategies/generate` NVIDIA NIM kod üretim endpoint'i
- `POST /api/v1/strategies/validate` AST tabanlı statik doğrulama endpoint'i
- `POST /api/v1/backtests/bist` güvenilir referans strateji backtest endpoint'i
- Yahoo Finance günlük BIST verisi, OHLCV temizliği ve kronolojik split
- Ağdan bağımsız backend testleri ve Türkçe dokümantasyon

Mobil uygulama henüz backend'e bağlanmaz. Day 4 backtest'i yalnızca repository
içindeki güvenilir stratejiyi kullanır; LLM kodu yürütme, indikatör referans
karşılaştırması ve güvenli runtime henüz yoktur.

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

## Day 4 piyasa verisi ve backtest akışı

```text
BIST sembolü
      ↓ allowlist + .IS
Yahoo Finance / yfinance
      ↓ yaklaşık 3 yıl, tamamlanmış günlük barlar
OHLCV Cleaner
      ↓
Kronolojik Split
      ↓ son 6 takvim ayı
ReferenceSmaCrossStrategy
      ↓
backtesting.py
      ↓ finalize_trades=True
JSON-safe performans metrikleri
      ↓
POST /api/v1/backtests/bist
```

Yahoo isteğinin exclusive bitişi BIST takvimindeki bugündür; potansiyel olarak
tamamlanmamış güncel mum istenmez. Backtest yalnızca son altı aylık test
DataFrame'ini alır. Test penceresi sonunda açık kalan trusted-strategy pozisyonu,
tarihsel rapora katılması için son barda finalize edilir.

## Statik doğrulama güvenlik sınırı

`ast.parse()` kaynak kodunu bir Abstract Syntax Tree'ye dönüştürür ve normal
Python ifadelerini çalıştırmaz. Sistem, izin verilen import köklerini, belirli
yasaklı çağrıları, `GeneratedStrategy` arayüzünü ve açık negatif `.shift(-N)`
kalıplarını kontrol eder.

LLM çıktısı güvenilir uygulama kodu değildir. AST doğrulaması yalnızca bilinen
bazı riskleri tespit eder; alias çözümü, kapsamlı veri akışı analizi veya eksiksiz
look-ahead tespiti yapmaz ve tam bir sandbox değildir. Bu aşamada üretilen kod
çalıştırılmamaktadır.

## Sonraki fazlarda tamamlanacak mimari

```text
Flutter Mobile
      ↓ HTTPS
FastAPI Backend
      ↓
LLM Provider (mevcut: NVIDIA NIM)
      ↓
Statik doğrulama
      ↓
İzole runtime / sandbox testi
      ↓
İndikatör referans karşılaştırması
      ↓
Doğrulanmış LLM stratejisi + piyasa verisi
      ↓
Güvenli backtest köprüsü
      ↓
Sonuçların Flutter'a döndürülmesi
```

`yfinance`, `ta` ve `backtesting.py` runtime dependency olarak eklenmiştir;
ancak `ta` Day 4 SMA stratejisinde kullanılmaz. Güvenli LLM yürütme ortamı,
indikatör karşılaştırması, Docker, Nginx ve VPS dağıtımı sonraki fazlardadır.

## Güvenlik ilkeleri

- Gizli değerler yalnızca sunucu tarafındaki ortam değişkenlerinde tutulur.
- Gerçek `.env` dosyaları ve API anahtarları Git'e eklenmez.
- Sağlayıcı hata ayrıntıları public API yanıtlarına taşınmaz.
- LLM çıktısı hiçbir zaman doğrudan çalıştırılabilir veya güvenilir kabul edilmez.
- Day 4 backtest endpoint'i kaynak kod kabul etmez; yalnızca sabit trusted
  strategy sınıfını kullanır.
- Gelecekteki yürütme aşaması, statik doğrulamadan ayrı bir izolasyon katmanı
  gerektirir.
