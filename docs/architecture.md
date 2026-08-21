# Sistem Mimarisi

## Mevcut uygulama

Repository şu bileşenleri içerir:

- Android/iOS hedefli, henüz backend'e bağlanmamış Flutter kabuğu
- FastAPI ve `GET /health`
- NVIDIA NIM `POST /api/v1/strategies/generate`
- AST tabanlı `POST /api/v1/strategies/validate`
- Trusted repository-owned `POST /api/v1/backtests/bist`
- Docker-isolated `POST /api/v1/strategy-lab/run`
- Flutter metadata `GET /api/v1/strategy-lab/capabilities`
- Yahoo Finance, OHLCV temizliği ve kronolojik son-altı-ay split'i
- Ağ, NVIDIA, Yahoo ve Docker gerektirmeyen pytest paketi

## İki ayrı execution yolu

### TRUSTED HOST PATH

```text
BIST symbol → Yahoo → clean/split → ReferenceSmaCrossStrategy
→ host backtesting.py → metrics → /api/v1/backtests/bist
```

Bu Day 4 tanı yolu yalnızca repository-owned sınıfı çalıştırır. Günlük Yahoo
isteğinin exclusive bitişi BIST takvimindeki bugündür; tamamlanmamış güncel mum
istenmez. Son altı aylık pencerede açık kalan pozisyon raporlama için
`finalize_trades=True` ile final barda kapatılır.

### UNTRUSTED GENERATED CODE SANDBOX PATH

```text
Prompt → NVIDIA → Generated source → static validation
→ bounded pre-test repair → deterministic sandbox smoke
→ strategy freeze → Yahoo → clean/split → held-out final six months
→ frozen strategy sandbox backtest → metrics → /api/v1/strategy-lab/run
```

Generated source FastAPI sürecinde import edilmez. Host, kodu read-only geçici
input mount'uyla Docker worker'a aktarır. Dinamik import yalnızca network-disabled,
read-only, non-root ve kaynak sınırlı konteyner içinde yapılır. Sandbox yoksa
yerel fallback bulunmaz.

## Static validation ve supported-indicator contract

`ast.parse()` kodu çalıştırmadan syntax tree üretir. Import allowlist, yasaklı
çağrılar, `GeneratedStrategy` interface'i ve açık negatif shift kontrol edilir.
Bu filtre alias/data-flow analizinin tamamını yapmadığından sandbox yerine geçmez.

Supported indicators SMA, EMA, RSI, MACD, Bollinger Bands, Stochastic ve ATR'dir.
Standart hesaplar `ta.trend`, `ta.momentum` ve `ta.volatility` implementasyonlarına
yönlendirilir. Bu bir supported-indicator contract'tır; keyfî özel formüllerin
tam sayısal doğrulaması değildir. Kapsamlı reference comparison gelecek fazdır.

## Repair, freeze ve held-out izolasyonu

En fazla üç toplam strateji sürümü vardır. Repair yalnızca statik hata veya
deterministik smoke failure için kullanılabilir. NVIDIA; özgün prompt, mevcut kod
ve güvenli pre-test bulgularından başka bilgi almaz.

Validation ve smoke geçtiğinde kaynak SHA-256 ile frozen olur. Market verisi bu
noktadan sonra indirilir. Worker smoke ve gerçek backtest kaynak hash'lerini
doğrular. Held-out altı aylık verideki hata repair başlatmaz; OHLCV, tarih,
runtime bulgusu veya metrik NVIDIA'ya gönderilmez.

## Docker sınırı

Worker protokolü `schema_version=1` tek JSON mesajıdır. Konteynerde network,
IPC, Linux capability ve privilege escalation kapalıdır; root filesystem
read-only, kullanıcı non-root, `/tmp` 32 MB ve CPU/bellek/PID/time/output/open-file
limitlidir. Yalnızca `strategy.py`, `data.csv` ve `request.json` taşıyan input
dizini read-only mount edilir. Repository, `.env`, home, Docker socket ve secret
mount edilmez.

Altı aylık günlük OHLCV küçük olduğu için worker interchange formatı CSV'dir.
Gelecekte büyük intraday veri için Parquet yalnızca ölçüm sonrasında
değerlendirilebilir.

## Flutter ve gelecek mimari

Flutter yalnızca FastAPI ile HTTPS/JSON üzerinden konuşacak; NVIDIA key, Yahoo
mantığı veya Python execution taşımayacaktır. Mevcut Strategy Lab MVP'si istemci
açısından uzun süren request/response modelidir. Flutter bilinçli timeout ve
loading/progress state kullanmalıdır.

Production/mobile ölçeğinde şu job-resource modeli değerlendirilebilir:

```text
POST /strategy-lab/jobs → 202 + job_id
→ background execution
→ GET /strategy-lab/jobs/{id}
```

Gerçek bidirectional olay ihtiyacı yoksa polling, WebSocket'ten önce tercih
edilmelidir. Day 5 job altyapısı, Redis, Celery, database, SSE veya WebSocket
uygulamaz.

## Güvenlik ve sonraki fazlar

- Secret'lar yalnızca backend environment'ında tutulur.
- Provider/worker traceback ve internal çıktıları public API'ye taşınmaz.
- Generated code host sürece hiçbir zaman alınmaz.
- Day 4 trusted endpoint'i generated source kabul etmez.
- Full indicator numerical comparison, Flutter networking/UI, auth, database,
  production deployment ve live trading sonraki fazlardır.
