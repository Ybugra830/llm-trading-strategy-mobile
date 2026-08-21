# LLM Tabanlı Teknik Analiz Strateji Üretici ve Backtest Sistemi

> **Güncel mimari kararı (2026):** Bu belge mevcut backend hedeflerini koruyarak istemci tarafını **Flutter mobil uygulama (Android + iOS)** olacak şekilde günceller. Repository monorepo yapısındadır: `backend/`, `mobile/`, `docs/`. Mobil uygulama NVIDIA NIM veya Yahoo Finance ile doğrudan konuşmaz; yalnızca FastAPI backend'e HTTP/HTTPS istekleri gönderir. API anahtarları ve finansal iş mantığı backend'de kalır.

## 1. Proje Adı

**LLM-Based Technical Analysis Strategy Generator, Validator and Backtesting Framework**

Türkçe adı:

**LLM Tabanlı Teknik Analiz Strateji Üretme, Doğrulama ve Backtest Sistemi**

---

## 2. Projenin Amacı

Bu projenin amacı, kullanıcının doğal dil ile yazdığı teknik analiz stratejilerini Python koduna dönüştüren, üretilen kodu güvenlik ve doğruluk açısından kontrol eden, unit testlerden geçiren ve geçmiş piyasa verileri üzerinde backtest ederek raporlayan bir yazılım sistemi geliştirmektir.

Kullanıcı sisteme şu şekilde bir istek girebilir:

```text
RSI 30 seviyesinin altına düştüğünde alış,
70 seviyesinin üzerine çıktığında satış yapan
bir Python stratejisi oluştur.
```

Sistem bu isteği analiz eder, uygun Python kodunu üretir, kodun geçerli ve güvenli olup olmadığını kontrol eder, teknik indikatör hesaplamalarını referans kütüphanelerle karşılaştırır ve stratejiyi geçmiş fiyat verileri üzerinde çalıştırır.

Temel işlem akışı:

```text
Kullanıcı isteği
      ↓
LLM ile strateji kodu üretimi
      ↓
Kod temizleme ve ayrıştırma
      ↓
Güvenlik kontrolü
      ↓
Sözdizimi kontrolü
      ↓
Unit testlerin çalıştırılması
      ↓
Referans indikatörle karşılaştırma
      ↓
Backtest
      ↓
Performans metriklerinin hesaplanması
      ↓
Rapor oluşturulması
```

---

## 3. Projenin Kapsamı

Proje aşağıdaki temel özellikleri içerecektir:

- Doğal dil ile teknik analiz stratejisi tanımlama
- LLM API kullanarak Python strateji kodu üretme
- Üretilen koddan Markdown işaretlerini temizleme
- Python sözdizimi kontrolü
- Tehlikeli kodların tespit edilmesi
- İzin verilmeyen importların engellenmesi
- İndikatör hesaplamalarının doğrulanması
- Unit testlerin otomatik çalıştırılması
- OHLCV piyasa verilerinin yüklenmesi
- Geçmiş veriler üzerinde backtest yapılması
- Performans metriklerinin hesaplanması
- Sonuçların JSON, tablo ve grafik olarak raporlanması
- FastAPI tabanlı servis sunulması
- Flutter tabanlı Android/iOS mobil istemci sunulması
- Mobil istemcinin yalnızca FastAPI API'si ile haberleşmesi
- BIST sembollerinin Yahoo Finance üzerinden `.IS` uzantısıyla geçmiş günlük OHLCV verisine bağlanması
- Yaklaşık son 3 yıllık verinin indirilmesi ve son 6 takvim ayının görülmemiş backtest dönemi olarak ayrılması

İlk sürümde desteklenecek indikatörler:

- SMA
- EMA
- RSI
- MACD
- Bollinger Bands
- Stochastic Oscillator
- ATR

İlk sürümde desteklenecek strateji işlemleri:

- Alış sinyali üretme
- Satış sinyali üretme
- Pozisyon açma
- Pozisyon kapatma
- Stop-loss tanımlama
- Take-profit tanımlama
- Komisyon oranı belirleme
- Başlangıç bakiyesi belirleme

---

## 4. Kullanılacak Teknolojiler

### Programlama Dili

- Python 3.11 veya üzeri

### Temel Kütüphaneler

- `pandas`
- `numpy`
- `pydantic`
- `pytest`
- `httpx`
- `python-dotenv`

### Teknik Analiz

- `ta`
- İsteğe bağlı olarak `TA-Lib`

### Backtest

- `backtesting.py`

Alternatif olarak ilerleyen aşamada:

- `vectorbt`
- `backtrader`

### API

- `FastAPI`
- `Uvicorn`

### Mobil İstemci

- `Flutter`
- `Dart`
- Hedef platformlar: **Android ve iOS**
- Mobil istemci yalnızca FastAPI backend'e HTTP/HTTPS istekleri gönderir.
- `NVIDIA_API_KEY` veya başka sunucu secret'ları mobil uygulamaya gömülmez.

### Grafik ve Raporlama

- `matplotlib`
- `plotly`
- `jinja2`

### Kod Analizi ve Güvenlik

- `ast`
- `subprocess`
- `tempfile`
- `resource`
- `signal`

### LLM API

Aşağıdaki servislerden biri kullanılabilir:

- OpenAI API
- Azure OpenAI
- Google Gemini API
- Anthropic API
- Yerel çalışan açık kaynaklı LLM

LLM sağlayıcısı doğrudan proje koduna bağlanmamalıdır. Tüm modeller ortak bir arayüz üzerinden kullanılmalıdır.

---

## 5. Sistem Mimarisi

```text
┌───────────────────────────────────┐
│      Flutter Mobil Uygulama       │
│         Android / iOS             │
└─────────────────┬─────────────────┘
                  │ HTTP / HTTPS
                  ▼
┌───────────────────────────────────┐
│             FastAPI               │
│  şema, routing, servis katmanı    │
└──────────┬──────────────┬─────────┘
           │              │
           │              └──────────────────────┐
           ▼                                     ▼
┌──────────────────────┐              ┌──────────────────────┐
│   Strateji Üretimi   │              │    Piyasa Verisi     │
│ Prompt Builder       │              │ Yahoo Finance        │
│ NVIDIA NIM / LLM     │              │ yfinance / BIST .IS  │
└──────────┬───────────┘              └──────────┬───────────┘
           ▼                                     ▼
┌──────────────────────┐              ┌──────────────────────┐
│ Code Cleaner + AST   │              │ OHLCV Cleaner        │
│ Security Validator   │              │ Kronolojik Split     │
│ Interface Validator  │              │ Son 6 ay test verisi │
└──────────┬───────────┘              └──────────┬───────────┘
           │                                     │
           └──────────────┬──────────────────────┘
                          ▼
              ┌────────────────────────┐
              │    Backtest Engine     │
              │    backtesting.py      │
              └────────────┬───────────┘
                           ▼
              ┌────────────────────────┐
              │  Performans Metrikleri │
              │ Sharpe / Sortino /     │
              │ Drawdown / Getiri ...  │
              └────────────┬───────────┘
                           │ JSON
                           ▼
              ┌────────────────────────┐
              │ Flutter Sonuç Ekranı   │
              └────────────────────────┘
```

### 5.1 Mobil istemci güvenlik sınırı

Flutter uygulaması:

- Kullanıcının BIST sembolü, strateji metni, başlangıç bakiyesi ve komisyon gibi girdilerini toplar.
- FastAPI endpoint'lerini çağırır.
- Üretilen strateji kodunu kullanıcı isterse salt okunur biçimde gösterebilir.
- Backtest sonuçlarını kartlar, tablo ve grafiklerle gösterir.
- NVIDIA NIM'e doğrudan bağlanmaz.
- Yahoo Finance/yfinance'a doğrudan bağlanmaz.
- API key, `.env`, LLM provider secret'ı veya backend güvenlik kuralları mobil uygulamaya taşınmaz.
- Gerçek alım-satım emri göndermez.

### 5.2 Flutter ilk sürüm ekranları

1. **Strategy Lab**
   - BIST sembol seçimi
   - Doğal dil strateji metni
   - Başlangıç bakiyesi
   - Komisyon
   - “Strateji Oluştur” butonu

2. **Validation**
   - Kod üretildi mi?
   - Syntax geçerli mi?
   - Import/güvenlik kontrolü geçti mi?
   - `GeneratedStrategy` arayüzü geçerli mi?
   - Hata mesajları
   - İsteğe bağlı “Kodu Gör”

3. **Backtest Sonucu**
   - Test tarih aralığı
   - Toplam getiri
   - Buy & Hold getirisi
   - Net kâr/zarar
   - Sharpe
   - Sortino
   - Maksimum Drawdown
   - İşlem sayısı
   - Win Rate
   - Profit Factor
   - İleride equity/drawdown grafikleri

4. **Bilgi / Hakkında**
   - Eğitim ve araştırma uyarısı
   - Verinin gerçek zaman garantisi olmadığı bilgisi
   - Geçmiş performansın geleceği garanti etmediği uyarısı

---

## 6. Önerilen Dosya Yapısı

Mevcut proje **monorepo** olarak tutulur. Backend'in sorumlulukları korunur; Flutter istemci ayrı `mobile/` klasöründedir.

```text
llm-trading-strategy-mobile/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   ├── schemas/
│   │   ├── llm/
│   │   ├── validators/
│   │   ├── market/
│   │   ├── backtest/
│   │   └── services/
│   ├── tests/
│   ├── scripts/
│   ├── .env.example
│   ├── pyproject.toml
│   └── README.md
│
├── mobile/
│   ├── android/
│   ├── ios/
│   ├── lib/
│   │   ├── main.dart
│   │   ├── app.dart
│   │   ├── core/
│   │   │   ├── api/
│   │   │   └── config/
│   │   └── features/
│   │       ├── strategy/
│   │       ├── validation/
│   │       └── backtest/
│   ├── test/
│   ├── pubspec.yaml
│   └── analysis_options.yaml
│
├── docs/
│   ├── architecture.md
│   ├── internship-plan.md
│   ├── ast-validation.md
│   └── day4-bist-backtest.md
│
├── .gitignore
└── README.md
```

Notlar:

- `backend/` Python/FastAPI iş mantığını taşır.
- `mobile/` yalnızca Android/iOS Flutter istemcisidir.
- Backend secret'ları `mobile/` altına kopyalanmaz.
- Docker, Nginx, VPS ve deployment dosyaları ileriki fazlarda eklenecektir.
- LLM tarafından üretilen keyfi Python kodunun çalıştırılması için sandbox/runtime izolasyonu ayrıca geliştirilecektir.

---

## 7. LLM Modülü

LLM modülü, kullanıcı isteğini alarak uygun strateji kodunu üretir.

Mevcut geliştirme sürümünde varsayılan sağlayıcı **NVIDIA NIM**, model ise yapılandırmadan gelen `openai/gpt-oss-20b` değeridir. NVIDIA NIM OpenAI uyumlu istemci üzerinden çağrılır. Sağlayıcı/model `.env` ve Settings üzerinden yapılandırılır; mobil istemci API anahtarını taşımaz.

Görevleri:

- Kullanıcı isteğini yapılandırmak
- Sistem promptunu hazırlamak
- İzin verilen kütüphaneleri modele bildirmek
- Beklenen sınıf ve fonksiyon yapısını tanımlamak
- LLM API isteğini göndermek
- Model cevabından yalnızca Python kodunu çıkarmak
- Gerekirse hatalı kodu yeniden düzelttirmek

Ortak LLM arayüzü:

```python
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):

    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError
```

Örnek strateji üretim çağrısı:

```python
user_prompt = (
    "RSI 30 seviyesinin altına düştüğünde alış, "
    "70 seviyesinin üzerine çıktığında satış yapan "
    "bir strateji oluştur."
)
```

LLM sistem talimatı:

```text
Sen teknik analiz stratejileri üreten bir Python kod asistanısın.

Yalnızca geçerli Python kodu üret.

Kod, backtesting.py kütüphanesi ile uyumlu olmalıdır.

Strateji sınıfı Strategy sınıfından türemelidir.

Kodda yalnızca aşağıdaki importlara izin vardır:
- pandas
- numpy
- backtesting
- ta

Dosya sistemi, ağ bağlantısı, işletim sistemi komutları,
subprocess, eval, exec ve dinamik import kullanma.

Çıktıda açıklama, Markdown veya kod bloğu işareti bulunmamalıdır.
```

---

## 8. Kod Üretim Standardı

```python
from backtesting import Strategy
from ta.momentum import RSIIndicator


class GeneratedStrategy(Strategy):
    rsi_period = 14
    buy_level = 30
    sell_level = 70

    def init(self):
        close = self.data.Close.s

        self.rsi = self.I(
            lambda values: RSIIndicator(
                values,
                window=self.rsi_period,
            ).rsi(),
            close,
        )

    def next(self):
        if self.rsi[-1] < self.buy_level and not self.position:
            self.buy()

        elif self.rsi[-1] > self.sell_level and self.position:
            self.position.close()
```

Zorunlu kurallar:

- Sınıf adı `GeneratedStrategy` olmalıdır.
- Sınıf `Strategy` sınıfından türemelidir.
- `init()` metodu bulunmalıdır.
- `next()` metodu bulunmalıdır.
- Kod doğrudan dosya okumamalıdır.
- Kod internet bağlantısı kurmamalıdır.
- Kod işletim sistemi komutu çalıştırmamalıdır.
- Kod sabit bir giriş-çıkış arayüzüne uymalıdır.

---

## 9. Güvenlik Kontrolü

LLM tarafından üretilen kod doğrudan çalıştırılmamalıdır.

Yasaklanacak importlar:

```text
os
sys
subprocess
socket
requests
httpx
urllib
shutil
pathlib
pickle
marshal
ctypes
importlib
builtins
```

Yasaklanacak fonksiyonlar:

```text
eval
exec
compile
open
input
__import__
globals
locals
getattr
setattr
delattr
```

Örnek AST kontrolü:

```python
import ast


FORBIDDEN_IMPORTS = {
    "os",
    "sys",
    "subprocess",
    "socket",
    "requests",
    "urllib",
    "pathlib",
    "pickle",
    "importlib",
}

FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "compile",
    "open",
    "__import__",
}


class SecurityValidator(ast.NodeVisitor):

    def __init__(self):
        self.errors = []

    def visit_Import(self, node):
        for alias in node.names:
            root_name = alias.name.split(".")[0]

            if root_name in FORBIDDEN_IMPORTS:
                self.errors.append(
                    f"Yasaklı import: {alias.name}"
                )

        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.errors.append(
                    f"Yasaklı fonksiyon: {node.func.id}"
                )

        self.generic_visit(node)
```

AST kontrolü tek başına yeterli değildir. Kod ayrıca sınırlı süre ve sınırlı kaynakla ayrı bir süreçte çalıştırılmalıdır.

---

## 10. Sözdizimi Kontrolü

```python
import ast


def validate_syntax(code: str) -> tuple[bool, str | None]:
    try:
        ast.parse(code)
        return True, None

    except SyntaxError as exc:
        return False, str(exc)
```

---

## 11. Unit Test Sistemi

Test türleri:

- Sözdizimi testi
- İzin verilen import testi
- Sınıf ve metot testi
- İndikatör değer testi
- Referans kütüphane karşılaştırması
- Boş ve eksik veri testleri
- Sabit fiyat testi
- Geçersiz parametre testi

Örnek RSI testi:

```python
import numpy as np
import pandas as pd
from ta.momentum import RSIIndicator

from app.indicators.rsi import calculate_rsi


def test_rsi_matches_reference():
    close = pd.Series(
        [
            100, 101, 102, 101, 104, 105, 103,
            106, 108, 107, 109, 110, 111, 108,
            112, 114, 113, 115, 117, 118,
        ]
    )

    expected = RSIIndicator(
        close=close,
        window=14,
    ).rsi()

    actual = calculate_rsi(
        close=close,
        period=14,
    )

    np.testing.assert_allclose(
        actual.dropna().to_numpy(),
        expected.dropna().to_numpy(),
        rtol=1e-5,
        atol=1e-5,
    )
```

---

## 12. Referans İndikatör Karşılaştırması

Üretilen veya elle yazılan indikatör kodu, `ta` ya da `TA-Lib` sonucu ile karşılaştırılacaktır.

Örnek sonuç:

```json
{
  "indicator": "RSI",
  "reference_library": "ta",
  "mean_absolute_error": 0.000012,
  "maximum_error": 0.000081,
  "tolerance": 0.0001,
  "passed": true
}
```

---

## 13. Sandbox Çalıştırma

Kodun ana FastAPI sürecinde doğrudan çalıştırılması güvenli değildir.

Önerilen sınırlar:

```text
Maksimum çalışma süresi: 10 saniye
Maksimum bellek: 256 MB
Maksimum çıktı: 1 MB
Ağ erişimi: Kapalı
Dosya sistemi: Geçici klasörle sınırlı
```

Önerilen akış:

```text
Ana FastAPI uygulaması
        ↓
Geçici strateji dosyası
        ↓
Sınırlı Docker konteyneri
        ↓
Pytest
        ↓
Backtest
        ↓
JSON sonuç
```

---

## 14. Veri Formatı

Zorunlu OHLCV kolonları:

```text
Date
Open
High
Low
Close
Volume
```

Örnek:

```csv
Date,Open,High,Low,Close,Volume
2025-01-01,100,104,98,102,15000
2025-01-02,102,106,101,105,17000
2025-01-03,105,107,103,104,16000
```

Kontroller:

- Kolonlar mevcut mu?
- Tarihler geçerli ve sıralı mı?
- Tekrarlanan tarih var mı?
- Fiyatlar negatif mi?
- `High`, `Low` değerinden küçük mü?
- Eksik değer var mı?
- Veri uzunluğu yeterli mi?

---

## 15. Backtest Motoru

```python
from backtesting import Backtest


def run_backtest(
    data,
    strategy_class,
    cash: float = 100_000,
    commission: float = 0.002,
):
    backtest = Backtest(
        data,
        strategy_class,
        cash=cash,
        commission=commission,
        exclusive_orders=True,
        trade_on_close=False,
        finalize_trades=True,
    )

    return backtest.run()
```

İlk sürüm varsayımları:

```text
Başlangıç bakiyesi: 100.000 TL
Komisyon: %0,2
Aynı anda açık pozisyon: 1
```

Bu değerler yalnızca yazılım test ortamı içindir.

Day 4, sonu tanımlı altı aylık tarihsel pencereyi raporladığı için açık kalan
pozisyon `finalize_trades=True` ile son mevcut barda kapatılır ve performans
istatistiklerine dahil edilir. Bu davranış yalnızca repository-owned güvenilir
referans strateji için kullanılır; LLM kaynak kodu FastAPI sürecinde çalıştırılmaz.

---

## 16. Performans Metrikleri

- Başlangıç bakiyesi
- Bitiş bakiyesi
- Net kâr veya zarar
- Toplam getiri
- Al ve tut getirisi
- İşlem sayısı
- Kazanma oranı
- Maksimum düşüş
- Sharpe oranı
- Sortino oranı
- Profit Factor
- En iyi işlem
- En kötü işlem
- Ortalama işlem süresi

Örnek:

```json
{
  "initial_cash": 100000,
  "final_equity": 112450,
  "net_profit": 12450,
  "return_percent": 12.45,
  "buy_and_hold_return_percent": 8.31,
  "number_of_trades": 18,
  "win_rate_percent": 55.56,
  "max_drawdown_percent": -6.82,
  "sharpe_ratio": 1.21
}
```

---

## 17. FastAPI Endpointleri

### Sağlık Kontrolü

```http
GET /health
```

### Strateji Üretme

```http
POST /api/v1/strategies/generate
```

Örnek:

```json
{
  "prompt": "RSI 30 altına düştüğünde al, 70 üzerine çıktığında sat."
}
```

### Kod Doğrulama

```http
POST /api/v1/strategies/validate
```

LLM çıktısını syntax, import, security, interface ve temel look-ahead kontrollerinden geçirir.

### BIST Backtest

```http
POST /api/v1/backtests/bist
```

Örnek:

```json
{
  "symbol": "THYAO",
  "initial_cash": 100000,
  "commission": 0.002
}
```

Day 4 sürümünde bu endpoint Yahoo Finance üzerinden BIST günlük OHLCV verisini alır, son 6 takvim ayını test seti olarak ayırır ve **repository-owned güvenilir referans stratejiyi** `backtesting.py` ile çalıştırır.

Günlük veri isteğinde BIST yerel takvimindeki bugün exclusive `end` olarak
kullanılır. Böylece potansiyel olarak tamamlanmamış güncel günlük bar tarihsel
backtest verisine dahil edilmez.

> Day 4 güvenlik sınırı: `/generate` çıktısındaki keyfi LLM kaynak kodu doğrudan
> bu endpoint'e verilmez. Bu endpoint yalnızca trusted repository-owned stratejiyi
> host üzerinde çalıştırmaya devam eder. Generated source için ayrı Day 5 Docker
> sandbox yolu kullanılır.

### Strategy Lab

```http
POST /api/v1/strategy-lab/run
```

Day 5 endpoint'i prompt, BIST sembolü, cash ve commission değerini alır. NVIDIA
üretimi, statik validation, en fazla üç toplam sürümlü pre-test repair,
deterministik Docker smoke testi, strategy freeze, Yahoo split ve frozen
generated-strategy sandbox backtest'ini tek response'ta birleştirir.

Gerçek altı aylık test dönemi held-out kalır. Bu verideki runtime failure repair
başlatmaz ve NVIDIA'ya OHLCV, tarih, hata veya metrik gönderilmez.

```http
GET /api/v1/strategy-lab/capabilities
```

Flutter için desteklenen sıralı BIST sembollerini, supported-indicator contract'ı,
default cash/commission ve prompt limitlerini secret içermeden döndürür.

### Planlanan Yerel CSV Backtest

```http
POST /api/v1/backtests/run
```

Kontrollü fixture/CSV ve ileriki sandbox akışında kullanılacak planlı endpoint'tir.

### Planlanan Raporlama

```http
GET /api/v1/reports/{backtest_id}
```

---

## 18. Hata Düzeltme Döngüsü

```text
Kod üret
   ↓
Doğrula
   ↓
Hata var mı?
   ├── Hayır → Test ve backtest
   └── Evet
         ↓
   Hata mesajını LLM'e gönder
         ↓
   Düzeltilmiş kod üret
         ↓
   Yeniden doğrula
```

Maksimum düzeltme denemesi:

```text
3
```

---

## 19. Geliştirme Aşamaları

### Gün 1 — Temel Kurulum ✅
- Monorepo (`backend/`, `mobile/`, `docs/`)
- FastAPI + `/health`
- pytest/httpx
- Flutter Android/iOS iskeleti
- Git/GitHub düzeni

### Gün 2 — NVIDIA NIM / LLM Entegrasyonu ✅
- `.env` / Settings
- NVIDIA NIM OpenAI uyumlu istemci
- `POST /api/v1/strategies/generate`
- Prompt builder
- Mock testleri

### Gün 3 — AST Doğrulama ve Güvenlik ✅
- `POST /api/v1/strategies/validate`
- Code cleaner
- `ast.parse()`
- Import allowlist
- Yasaklı çağrılar
- `GeneratedStrategy`, `Strategy`, `init()`, `next()`
- Temel negatif `.shift(-N)` kontrolü

### Gün 4 — BIST Verisi ve Güvenilir Backtest Pipeline'ı
- `yfinance`
- BIST `.IS`
- Yaklaşık 3 yıl günlük düzeltilmiş OHLCV
- Bugünü exclusive bitiş alarak yalnızca tamamlanmış günlük barları indirme
- DataFrame temizliği
- Son 6 takvim ayı test seti
- Repository-owned SMA referans stratejisi
- `backtesting.py`
- Test penceresinin sonundaki açık trusted-strategy pozisyonunu finalize etme
- JSON-safe performans metrikleri
- `POST /api/v1/backtests/bist`

### Gün 5 — Güvenli Runtime ve Strategy Lab ✅
- Generated source'u FastAPI sürecinde çalıştırmama
- Network-disabled, read-only, non-root Docker sandbox
- Süre, bellek, CPU, PID, output, IPC ve open-file sınırları
- Versiyonlu worker JSON protokolü
- Deterministik runtime smoke testi
- En fazla üç toplam sürümlü pre-test repair
- Supported-indicator contract
- SHA-256 strategy freeze point
- Held-out son altı ayda repair olmadan tek değerlendirme
- `POST /api/v1/strategy-lab/run`
- `GET /api/v1/strategy-lab/capabilities`

### Sonraki Faz — Kapsamlı İndikatör Referans Doğrulaması
- RSI/SMA/EMA/MACD/Bollinger/Stochastic/ATR sonuçlarını `ta` referansıyla karşılaştırma
- Tolerans kontrolleri
- Keyfî özel formüllerin açık matematiksel doğrulaması

### Sonraki Faz — Flutter API Entegrasyonu
- Backend base URL
- Strategy Lab
- `/generate`
- `/validate`
- `/backtests/bist`
- Loading/error state
- Sonuç kartları ve grafikler

### Sonraki Faz — Deployment
- Ubuntu VPS
- Docker / Docker Compose
- Nginx
- HTTPS / Let's Encrypt
- GitHub Actions
- Flutter'ın public HTTPS FastAPI'ye bağlanması

---

## 20. Minimum Çalışan Ürün

Hedef uçtan uca mobil akış:

```text
Flutter'da kullanıcı stratejiyi doğal dilde yazar
        ↓
FastAPI /strategies/generate
        ↓
NVIDIA NIM Python kodu üretir
        ↓
Kod temizlenir
        ↓
AST / güvenlik / interface doğrulaması
        ↓
Güvenli runtime/sandbox testi
        ↓
BIST Yahoo Finance OHLCV verisi
        ↓
Son 6 ay görülmemiş test dönemi
        ↓
backtesting.py
        ↓
JSON performans metrikleri
        ↓
Flutter sonuç ekranı
```

Day 4'te piyasa verisi ve backtest motoru önce **repository-owned güvenilir referans strateji** ile doğrulanır. LLM kaynak kodunun gerçek backtest motoruna bağlanması sandbox/runtime fazından sonra yapılır.

---

## 21. Örnek Proje Çıktısı

```json
{
  "request": {
    "prompt": "RSI 30 altındayken al ve 70 üzerindeyken sat."
  },
  "generation": {
    "model": "default",
    "attempt_count": 1,
    "code_generated": true
  },
  "validation": {
    "syntax_valid": true,
    "security_valid": true,
    "interface_valid": true
  },
  "tests": {
    "passed": 8,
    "failed": 0,
    "duration_seconds": 1.42
  },
  "indicator_comparison": {
    "indicator": "RSI",
    "reference": "ta",
    "passed": true,
    "maximum_error": 0.00008
  },
  "backtest": {
    "initial_cash": 100000,
    "final_equity": 108450,
    "return_percent": 8.45,
    "number_of_trades": 12,
    "win_rate_percent": 58.33,
    "max_drawdown_percent": -5.20
  },
  "status": "success"
}
```

---

## 22. Kurulum

```bash
git clone <repository-url>
cd llm-trading-strategy-mobile
```

### Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
```

`.env`:

```env
NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
NVIDIA_MODEL=openai/gpt-oss-20b
NVIDIA_MAX_TOKENS=2048
```

Gerçek API anahtarı `.env.example`, kaynak kod, test veya Git geçmişine yazılmaz.

```powershell
pytest
uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

### Flutter Mobile

```powershell
cd mobile
flutter pub get
flutter analyze
flutter test
flutter run
```

İlk hedefler yalnızca Android ve iOS'tur. Mobil uygulama NVIDIA API anahtarını içermez. Yerel cihaz/emulator backend'e platforma uygun base URL ile bağlanır; production'da HTTPS public API URL kullanılır.

---

## 23. Backend Bağımlılık Özeti

Mevcut backend `pyproject.toml` kullanır.

```text
fastapi
uvicorn[standard]
openai
pydantic-settings
httpx (dev)
pytest (dev)
pandas
numpy
ta
backtesting
yfinance
```

Henüz kullanılmayan raporlama/deployment paketleri sırf planda var diye eklenmemelidir.

---

## 24. Başarı Kriterleri

- Doğal dil isteğinden strateji kodu üretilebilmesi
- Üretilen kodun güvenlik filtresinden geçirilmesi
- Geçersiz sözdiziminin yakalanması
- Yasaklı importların engellenmesi
- İndikatör değerlerinin referans kütüphaneyle eşleşmesi
- Unit test sonuçlarının raporlanması
- Backtest işleminin tamamlanması
- Performans metriklerinin hesaplanması
- API üzerinden uçtan uca çalışması
- Flutter mobil istemcinin backend API'sine bağlanabilmesi
- Kullanıcının mobil arayüzden strateji üretimi, doğrulama ve backtest sonucunu görebilmesi
- Mobil uygulamada hiçbir backend secret/API key bulunmaması
- En az RSI, MACD ve hareketli ortalama stratejilerinin desteklenmesi

---

## 25. Riskler ve Sınırlamalar

### LLM Hataları

LLM geçersiz veya mantıksal olarak hatalı kod üretebilir.

Önlemler:

- Sabit kod sözleşmesi
- AST doğrulaması
- Unit test
- Referans karşılaştırması
- Sınırlı düzeltme döngüsü

### Kod Güvenliği

Önlemler:

- İzin verilen import listesi
- Yasaklı fonksiyon listesi
- AST kontrolü
- Ayrı süreç
- Docker sandbox
- Süre ve bellek sınırı

### Geleceği Görme Yanlılığı

Önlemler:

- Sinyaller yalnızca mevcut ve geçmiş veriden üretilmeli
- Negatif kaydırma yasaklanmalı
- Backtest veri erişimi kontrol edilmeli

### Aşırı Uyum

Önlemler:

- Eğitim ve test dönemi ayrılmalı
- Out-of-sample test yapılmalı
- Walk-forward test eklenmeli
- Parametre sayısı sınırlanmalı

---

## 26. Staj Çıktıları

- Çalışan Python kütüphanesi
- FastAPI servisi
- Flutter Android/iOS mobil istemci
- LLM strateji üretim modülü
- Güvenlik doğrulama modülü
- Unit test paketi
- Backtest motoru
- Örnek veri setleri
- HTML ve JSON raporları
- API dokümantasyonu
- Mimari doküman
- Staj raporu
- Proje sunumu
- GitHub deposu

---

## 27. Hocaya Sunulabilecek Proje Özeti

Bu projede, kullanıcıların doğal dil ile tanımladıkları teknik analiz stratejilerini Python koduna dönüştüren LLM tabanlı bir sistem geliştirilecektir. Üretilen strateji kodları doğrudan çalıştırılmayacak; öncelikle sözdizimi, güvenlik, izin verilen importlar ve beklenen sınıf yapısı açısından doğrulanacaktır. Ardından unit testler çalıştırılacak ve RSI, MACD, SMA, EMA gibi teknik indikatörlerin sonuçları güvenilir teknik analiz kütüphaneleriyle karşılaştırılacaktır. Doğrulama aşamasını geçen stratejiler, geçmiş OHLCV piyasa verileri üzerinde backtest edilerek toplam getiri, işlem sayısı, kazanma oranı, maksimum düşüş ve Sharpe oranı gibi performans metrikleriyle raporlanacaktır. Sistem FastAPI tabanlı backend ve Android/iOS Flutter mobil istemci olarak sunulacak; ilerleyen aşamalarda farklı LLM sağlayıcıları, yeni indikatörler ve gelişmiş backtest yöntemleriyle genişletilebilecektir.

---

## 28. Güncel Uygulama Durumu ve Kod Üreticiye Verilecek Sınırlar

Bu belge Codex/AI coding agent tarafından okunacaksa aşağıdaki sınırlar korunmalıdır:

- Mevcut backend davranışları sebepsiz yere yeniden yazılmamalıdır.
- Day 1–3 endpoint'leri korunmalıdır.
- `mobile/` Day 4–5 backend çalışmasında değiştirilmemelidir.
- Day 4'te LLM kaynak kodu backtest motorunda çalıştırılmamalıdır.
- Yahoo Finance bağlantısı yalnızca backend'de olmalıdır.
- Flutter istemci Yahoo/NVIDIA'ya doğrudan bağlanmamalıdır.
- `.env` ve secret'lar Git'e eklenmemelidir.
- `pytest` internet/NVIDIA/Yahoo/Docker bağlantısına bağımlı olmamalıdır.
- Gerçek Yahoo testi manuel yapılmalı; unit/API testlerinde provider mock/fake edilmelidir.
- Generated source FastAPI sürecinde hiçbir zaman `exec`, `eval`, `compile` veya
  dinamik import ile yürütülmemelidir; yalnızca izole worker bunu yükleyebilir.

### Day 4 başlangıç kabulü

Day 4 öncesinde mevcut test paketi temiz olmalıdır. Kullanıcının mevcut çalışma durumunda Day 4 planı hazırlanırken **57 test geçiyordu**. Bu sayı gelecekte yeni testler eklendikçe artabilir; önemli olan regresyon olmamasıdır.

---

## 29. Flutter Mobil Arayüz Hedefi

Mobil uygulamanın amacı profesyonel broker terminali olmak değildir. İlk sürüm şu soruya cevap verir:

> “Aklımdaki teknik analiz stratejisini doğal dille yazarsam, sistem bunu güvenli bir stratejiye dönüştürüp geçmiş BIST verisinde nasıl performans gösterdiğini gösterebilir mi?”

Önerilen kullanıcı akışı:

```text
Strategy Lab
   ↓
Strateji üret
   ↓
Validation sonucu
   ↓
BIST + bakiye + komisyon seç
   ↓
Backtest çalıştır
   ↓
Getiri / risk / işlem metrikleri
```

Flutter tarafında ilk sürümde:

- Karmaşık finans terminali yapılmaz.
- Gerçek zamanlı fiyat akışı zorunlu değildir.
- Gerçek emir/broker entegrasyonu yapılmaz.
- Kod editörü zorunlu değildir; üretilen kod salt okunur gösterilebilir.
- Öncelik sade input, durum göstergeleri ve anlaşılır sonuç kartlarıdır.

---

## 30. Uyarı

Bu proje eğitim ve araştırma amacıyla geliştirilmektedir.

Üretilen stratejiler yatırım tavsiyesi değildir. Geçmiş performans gelecekteki performansı garanti etmez. Gerçek para ile işlem yapılmadan önce ayrıca risk analizi, güvenlik testi ve yasal uygunluk değerlendirmesi yapılmalıdır.
