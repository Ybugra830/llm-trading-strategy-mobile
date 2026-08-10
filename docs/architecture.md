# Sistem Mimarisi

## Amaç

LLM Trading Strategy Mobile; kullanıcının teknik analiz stratejisi oluşturma,
doğrulama ve geçmiş veriler üzerinde değerlendirme süreçlerini mobil cihazdan
yönetebilmesini hedefler. Mevcut aşama yalnızca uygulama sınırlarını ve
çalıştırılabilir iskeleti tanımlar.

## Bileşenler

### Flutter mobil uygulaması

- Android ve iOS kullanıcı arayüzünü sağlar.
- İleride strateji girdilerini backend'e iletir ve sonuçları gösterir.
- API anahtarı veya Azure OpenAI kimlik bilgisi saklamaz.

### FastAPI backend

- Mobile uygulaması için HTTP API katmanı olacaktır.
- Azure OpenAI, piyasa verisi, teknik analiz ve backtest işlemlerini ileride
  ayrı servis/modül sınırlarıyla yönetecektir.
- İlk aşamada yalnızca `GET /health` sağlık kontrolünü sunar.

### Planlanan harici bileşenler

- Azure OpenAI: Strateji taslağı üretimi ve doğal dil etkileşimi
- `yfinance`: Geçmiş piyasa verilerinin alınması
- `ta`: Teknik indikatörlerin hesaplanması
- `backtesting.py`: Stratejilerin geçmiş verilerle değerlendirilmesi
- Docker ve Nginx: Ubuntu VPS üzerinde paketleme, ters proxy ve yayınlama

Bu bileşenler henüz bağımlılık veya uygulama kodu olarak eklenmemiştir.

## Planlanan veri akışı

1. Kullanıcı mobile uygulamasında strateji isteğini oluşturur.
2. Mobile uygulaması isteği FastAPI backend'e gönderir.
3. Backend girdiyi doğrular ve gerekli piyasa verisini alır.
4. Azure OpenAI strateji taslağını üretir.
5. Backend taslağı güvenli ve çalıştırılabilir bir strateji modeline dönüştürür.
6. Teknik analiz ve backtest katmanları sonucu hesaplar.
7. Özet sonuç backend üzerinden mobile uygulamasına döner.

Bu akış hedef mimariyi gösterir; mevcut iskelette yalnızca sağlık kontrolü
çalışır.

## Güvenlik ilkeleri

- Secrets yalnızca sunucu tarafındaki ortam değişkenlerinden okunacaktır.
- Gerçek `.env` dosyaları ve API anahtarları Git'e eklenmeyecektir.
- Mobile uygulamasına sağlayıcı kimlik bilgisi gömülmeyecektir.
- LLM çıktısı doğrudan güvenilir veya çalıştırılabilir kod kabul edilmeyecektir.
