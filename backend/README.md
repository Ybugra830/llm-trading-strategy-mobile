# Backend

Bu dizin, projenin Python 3.11+ ve FastAPI tabanlı backend uygulamasıdır.
Mevcut aşamada sağlık kontrolü, NVIDIA NIM üzerinden Python strateji kodu
üretimi, AST tabanlı statik kod doğrulaması ve güvenilir repository-owned
stratejiyle BIST tarihsel backtest'i bulunur.

> LLM çıktısı güvenilir uygulama kodu değildir. Bu aşamada üretilen kod
> çalıştırılmamaktadır. AST kontrolü bir sandbox değildir. Day 4 backtest'i
> yalnızca backend içinde tanımlanmış güvenilir referans stratejiyi çalıştırır.

## Kurulum ve ortam yapılandırması

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Yerel `.env` dosyasındaki `NVIDIA_API_KEY` değerini kendi NVIDIA API
anahtarınızla doldurun. Gerçek anahtarı Git'e eklemeyin.

Backend öncelikle `backend/.env`, geriye uyumluluk için de depo kökündeki `.env`
dosyasını okur. Sistem ortam değişkenleri her iki dosyadan da önceliklidir.

## Çalıştırma

```powershell
uvicorn app.main:app --reload
```

Sağlık kontrolü `GET http://127.0.0.1:8000/health` adresindedir.

## Swagger ile strateji üretimini deneme

Uygulama çalışırken `http://127.0.0.1:8000/docs` adresini açın. Buradaki
`POST /api/v1/strategies/generate` endpoint'inde **Try it out** seçeneğini
kullanarak örneğin aşağıdaki isteği gönderin:

```json
{
  "prompt": "RSI 30 altındayken al, RSI 70 üzerindeyken sat."
}
```

Yanıttaki `code` alanı LLM tarafından üretilen, henüz güvenilir kabul edilmeyen
Python kaynak kodudur.

## Statik strateji doğrulaması

`POST /api/v1/strategies/validate`, gönderilen Python kaynak kodunu çalıştırmadan
analiz eder. Örnek istek:

```json
{
  "code": "from backtesting import Strategy\n\nclass GeneratedStrategy(Strategy):\n    def init(self):\n        pass\n\n    def next(self):\n        pass"
}
```

Başarılı doğrulama yanıtı:

```json
{
  "valid": true,
  "syntax_valid": true,
  "imports_valid": true,
  "security_valid": true,
  "interface_valid": true,
  "lookahead_valid": true,
  "errors": []
}
```

Güvensiz veya geçersiz kod normal uygulama sonucudur; HTTP 200 ve
`valid=false` döner. Yalnızca boş, eksik veya 20.000 karakterden uzun `code`
alanı gibi hatalı API verileri HTTP 422 döndürür.

### Statik doğrulama politikası

- İzin verilen import kökleri: `backtesting`, `ta`, `pandas`, `numpy`
- Yasaklı doğrudan çağrılar: `eval`, `exec`, `compile`, `open`, `input`,
  `globals`, `locals`, `getattr`, `setattr`, `delattr`, `__import__`
- Açıkça yasaklı attribute çağrıları: `os.system`, `subprocess.run`,
  `subprocess.Popen`
- Sınıf adı tam olarak `GeneratedStrategy` olmalıdır.
- Sınıf `Strategy` veya `backtesting.Strategy` tabanından türemelidir.
- Sınıf doğrudan `init()` ve `next()` metotlarını tanımlamalıdır.
- Literal negatif `.shift(-N)` çağrıları olası look-ahead kullanımı olarak
  işaretlenir; `series[-1]` ve `series[-2]` bu nedenle reddedilmez.

Kaynak kodu yalnızca `ast.parse()` ile sözdizimi ağacına dönüştürülür. `exec`,
`eval`, `compile`, subprocess veya dinamik import kullanılmaz. AST kontrolü
riski azaltır fakat keyfî Python çalıştırmak için güvenli bir sandbox sağlamaz.

## BIST tarihsel backtest

`POST /api/v1/backtests/bist`, desteklenen BIST sembolünü Yahoo Finance `.IS`
ticker'ına dönüştürür, yaklaşık üç yıllık tamamlanmış günlük düzeltilmiş OHLCV
verisini indirir ve son altı takvim ayını test dönemi olarak kullanır.

Desteklenen semboller:

```text
THYAO ASELS TUPRS BIMAS EREGL KCHOL GARAN AKBNK SISE SAHOL FROTO TOASO
```

Örnek istek:

```json
{
  "symbol": "THYAO",
  "initial_cash": 100000,
  "commission": 0.002
}
```

PowerShell örneği:

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/api/v1/backtests/bist `
  -ContentType "application/json" `
  -Body '{"symbol":"THYAO","initial_cash":100000,"commission":0.002}'
```

Yahoo isteğinde `end` olarak BIST yerel takvimindeki bugün kullanılır. yfinance
bu değeri exclusive yorumladığı için mevcut günün potansiyel olarak tamamlanmamış
barı istenmez. Split, temiz verinin son tarihinden altı takvim ayı geriye gider;
history boş olamaz ve test döneminde en az 60 bar bulunmalıdır.

Backtest yapılandırması:

- `ReferenceSmaCrossStrategy`: SMA 10 / SMA 20, long-only
- `cash`: request içindeki başlangıç bakiyesi
- `commission`: request içindeki oran
- `exclusive_orders=True`
- `trade_on_close=False`
- `finalize_trades=True`

Son parametre, sınırı belli tarihsel test penceresinin sonundaki açık pozisyonu
son mevcut barda kapatarak rapor metriklerine dahil eder. Dönen metrikler final
equity, net profit, return, buy-and-hold, işlem sayısı, win rate, max drawdown,
Sharpe, Sortino, Profit Factor, best/worst trade, average trade duration ve
exposure time alanlarını içerir. Hesaplanamayan değerler `null` olur; sıfır
işlem backend hatası değildir.

Gerçek veriyi production modülleriyle incelemek için:

```powershell
python scripts/inspect_bist_data.py THYAO
```

Script ilk/son tamamlanmış piyasa tarihini, kolonları, head/tail ve kronolojik
split bilgilerini gösterir. Pytest gerçek Yahoo ağına bağlanmaz.

`ta` planlanan RSI, EMA, MACD, Bollinger, Stochastic ve ATR doğrulamaları için
runtime dependency'dir. Day 4 güvenilir SMA stratejisi `ta` kullanmaz.

Day 4, tam LLM → backtest entegrasyonunun son aşaması değildir. Day 4'te yalnızca
güvenilir repository-owned referans stratejisi çalıştırılır. LLM tarafından
üretilen Python kodu Day 4 FastAPI sürecinde çalıştırılmaz.

## NVIDIA bağlantı tanısı

FastAPI'den bağımsız bağlantı kontrolü için backend dizininden çalıştırın:

```powershell
python scripts/check_nvidia_connection.py
```

Script API anahtarını göstermez. Yalnızca anahtarın bulunup bulunmadığını,
uzunluğunu, base URL'yi, modeli, token sınırını ve güvenli sağlayıcı sonucunu
yazar. Başarılı sonuç modelin NVIDIA hosted endpoint tarafından kabul edildiğini
ve metin yanıtı alındığını doğrular.

Sağlayıcı hatalarında public API yanıtı güvenli ve genel kalır. Sunucu terminali
ve tanı scripti şu ayrıntıları gösterebilir:

- `401 AuthenticationError`: anahtar geçersiz, süresi dolmuş veya iptal edilmiş olabilir.
- `403 PermissionDeniedError`: anahtar bu endpoint/model için yetkisiz olabilir.
- `404 NotFoundError`: base URL veya model kimliği sağlayıcıda bulunamamış olabilir.
- `400 BadRequestError`: istek parametrelerinden biri sağlayıcı tarafından reddedilmiştir.
- `429 RateLimitError`: NVIDIA kullanım limiti aşılmıştır.
- `APIConnectionError` / `APITimeoutError`: DNS, firewall, proxy veya ağ erişimi sorunu olabilir.

Loglar exception türünü, varsa HTTP durumunu ve request ID'yi içerir; API
anahtarı, Authorization header veya `.env` içeriği loglanmaz.

## Test

```powershell
pytest
```

Testler gerçek NVIDIA API anahtarı, Yahoo Finance veya dış ağ bağlantısı kullanmaz.

## Veri ve yatırım uyarısı

`yfinance`, Yahoo Finance verisine erişen topluluk projesidir; Yahoo tarafından
desteklenen resmî bir istemci değildir. Verinin gerçek zaman, doğruluk veya
kesintisiz erişim garantisi yoktur. Bu proje eğitim ve araştırma amaçlıdır,
gerçek emir göndermez ve yatırım tavsiyesi değildir. Geçmiş performans gelecekteki
performansı garanti etmez.
