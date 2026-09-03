# Strategy Lab Backend Hardening Raporu

Tarih: 25 Ağustos 2026

## Sonuç ve deployment kararı

Backend hardening uygulanmış, ancak deployment yapılmamıştır. Deployment kararı
**UNSAFE**'tır. Ana 180-koşuluk gerçek matris `GATE=FAIL` üretmiştir: sekiz
NVIDIA provider çağrısı HTTP 502 ile sonuçlanmış ve Türkçe MACD promptu first-pass
eşiğini kaçırmıştır. Ana matristen sonra bulunan provider timeout/retry ve Docker
cold-start sınıflandırma sorunları final kodda düzeltilmiş, fakat bu final kodla
180 koşunun tamamı yeniden PASS olmamıştır.

Final kodla yapılan küçük gerçek EN/TR SMA smoke matrisi 2/2 HTTP 200, 2/2
first-pass ve sıfır repair ile geçmiştir. Bu sonuç ana kabul kapısının yerine
geçmez.

## Phase 1: pre-hardening tanı

Aşağıdaki promptlar gerçek FastAPI route'u, configured NVIDIA modeli,
production static validation, Docker worker, Yahoo ve backtest bileşenleriyle
10'ar kez çalıştırıldı:

- EN: `Buy when the 20-day moving average crosses the 50-day moving average upwards, close the position when it crosses downwards.`
- TR: `20 günlük hareketli ortalama 50 günlük hareketli ortalamayı yukarı kestiğinde al, aşağı kestiğinde pozisyonu kapat.`

Sonuçlar:

| Dil | HTTP 200 | HTTP 422 | HTTP 502 | Üretilen sürüm | Sürüm başına ortak sonuç |
|---|---:|---:|---:|---:|---|
| EN | 0/10 | 10/10 | 0/10 | 30 | static valid, smoke failure |
| TR | 0/10 | 9/10 | 1/10 | 28 | static valid, smoke failure |

İzole diagnostik Docker replay tüm 58 sürümde aynı kök nedeni doğruladı:

- 58/58 kaynak `SMAIndicator(...).sma()` kullandı.
- `ta.trend.SMAIndicator` için geçerli API `sma_indicator()`'dır.
- 58/58 kaynak static AST doğrulamasını geçti.
- 58/58 kaynak smoke sırasında `AttributeError` zinciriyle başarısız oldu.
- 12/58 kaynak doğrudan crossover koşulu kullandı; geri kalanların bir bölümü
  crossover boolean'larını gereksiz biçimde `self.I` ile kaydetti.
- TR'deki tek HTTP 502, ilk smoke failure sonrasındaki repair provider çağrısında
  NVIDIA 429 nedeniyle oluştu; dil semantiğinin doğrudan kanıtı değildi.

Bu sonuçlar üç root-cause kümesi oluşturdu:

1. Prompt contract doğru `ta` method adını ve adapter modelini yeterince açık
   belirtmiyordu.
2. Generic repair aynı hatalı API kalıbını tekrarlayabiliyor, runtime failure
   türü ve indicator family bilgisi almıyordu.
3. Static AST validator güvenlik/sözdizimi/interface kontrolü yapıyor, fakat
   izinli bir sınıftaki var olmayan method adını type-check etmiyordu.

Pre-hardening generated source ve replay kayıtları Git tarafından izlenmeyen
`reports/strategy-reliability/20260824-201514/pre-hardening/` dizisindedir.

## Uygulanan hardening

### Bilingual compositional prompt contract

`app/llm/prompt_builder.py` artık İngilizce ve Türkçe girdilerin aynı trading
semantiğine normalize edilmesini açıkça ister. Contract şunları zorunlu kılar:

- `GeneratedStrategy(Strategy)`, doğrudan `init()` ve `next()`;
- `Strategy.__init__` override yasağı;
- tüm numeric indicator output'larının `self.I(...)` ile `init()` içinde kaydı;
- `self.data.*` girdilerinin helper içinde `pandas.Series`'e çevrilmesi;
- aynı uzunlukta NumPy-compatible helper output'u;
- `next()` içinde indicator hesaplamama;
- long-only girişte `self.buy()`, çıkışta yalnız `self.position.close()`;
- crossover için açık `[-2]` / `[-1]` karşılaştırması;
- exact `ta` API method adları.

`app/llm/prompt_examples.py`, RSI, SMA, EMA, MACD, Bollinger Bands,
Stochastic ve ATR için EN/TR eş-anlamlı prompt çiftleri ile tek repository-owned
canonical Python uygulaması taşır.

### Güvenli repair context

`RepairFailureContext` immutable bir internal modeldir. Repair'e yalnız şu
allowlisted bağlam gider:

- stage: `static` veya `smoke`;
- normalize failure type;
- AST/prompt üzerinden deterministik indicator family;
- bounded safe findings;
- family-specific compatibility guidance.

Raw exception metni, traceback, Docker komutu, environment, API key, market
satırları ve held-out veri repair promptuna girmez. Syntax parse failure artık
diğer validator flag'lerini topluca raporlamak yerine yalnız
`SyntaxValidationError` olarak önceliklendirilir.

### Sandbox protocol v2 ve cold-start ayrımı

Host/worker protocol schema v2'ye geçirilmiştir. Worker runtime failure için
yalnız şu sınıfları döndürebilir:

`AttributeError`, `TypeError`, `ValueError`, `IndexError`, `KeyError`,
`RuntimeError`, `ZeroDivisionError`, `OverflowError`, `UnknownRuntimeError`.

Mesaj ve traceback dönmez. Interface yükleme hataları özel internal sınıflarla
runtime `TypeError`'dan ayrılır.

Ana matriste üç Docker smoke host timeout'u görüldü. Bunlar generated strategy
CPU süresinden değil Docker Desktop cold-start gecikmesinden kaynaklanıyordu ve
yanlışlıkla repair tetikliyordu. Final uygulama bunu şu şekilde ayırır:

- `SANDBOX_TIMEOUT_SECONDS=10`: worker içinde `SIGALRM` ile source load +
  backtest için gerçek strateji çalışma sınırı;
- `SANDBOX_STARTUP_GRACE_SECONDS=20`: yalnız host/container cold-start bütçesi;
- host toplam bütçeyi aşarsa `SANDBOX_UNAVAILABLE` ve HTTP 503 yolu;
- cold-start payı generated source'a ek CPU süresi vermez.

Docker-only execution, `--network=none`, read-only root, non-root user,
capability drop, no-new-privileges, memory/CPU/PID/output/IPC/open-file sınırları
ve local execution fallback yasağı korunmuştur.

### Provider sınırları

Ana matris explicit SDK timeout bulunmadığını ve OpenAI SDK varsayılan retry
zincirinin route süresini aşabildiğini gösterdi. Final uygulamada:

- `NVIDIA_REQUEST_TIMEOUT_SECONDS=120` yapılandırılabilir sert sınırdır;
- `AsyncOpenAI(max_retries=0)` ile örtük retry kapalıdır;
- reliability runner ayrıca ASGI çağrısını `asyncio.wait_for` ile wall-clock
  olarak sınırlar.

Model, `temperature=0.1`, `NVIDIA_MAX_TOKENS=2048` ve en fazla üç strategy
version değiştirilmemiştir.

## 180-run post-hardening reliability matrisi

Ana matris 9 prompt x 20 sıralı çağrıdan oluşur. Her çağrı THYAO, 100000 cash ve
0.002 commission ile gerçek FastAPI route'undan geçmiştir. Hidden runner retry
yoktur.

| Prompt | Final HTTP 200 | First-pass | Repair 0/1/2 | Kapı |
|---|---:|---:|---:|---|
| EN RSI | 15/20 | 15/20 (75%) | 20/0/0 | FAIL |
| EN SMA | 20/20 | 19/20 (95%) | 19/1/0 | PASS |
| EN EMA | 20/20 | 20/20 (100%) | 20/0/0 | PASS |
| EN MACD | 20/20 | 20/20 (100%) | 20/0/0 | PASS |
| EN Bollinger + RSI | 20/20 | 20/20 (100%) | 20/0/0 | PASS |
| TR RSI | 20/20 | 19/20 (95%) | 19/1/0 | PASS |
| TR SMA | 20/20 | 20/20 (100%) | 20/0/0 | PASS |
| TR EMA | 20/20 | 20/20 (100%) | 20/0/0 | PASS |
| TR MACD | 17/20 | 12/20 (60%) | 15/5/0 | FAIL |

Toplam:

- 180 scheduled run;
- 172 HTTP 200 (%95,56);
- 165 scheduled first-pass (%91,67);
- 8 provider HTTP 502, 0 attempt;
- 7 repair: 3 smoke timeout + 4 syntax/prose-fence failure;
- repair dağılımı: 173/7/0 (`0/1/2`);
- zero unknown/unclassified failure;
- zero final HTTP 422, HTTP 503, HTTP 500 veya market-data failure.

Provider failure koşuları EN-RSI 11, 12, 18, 19, 20 ve TR-MACD 3, 4, 5'tir.
Üretilmiş bir initial version'a ulaşan 172 çağrının tamamı sonunda HTTP 200
döndürmüştür. Bu, generation pipeline iyileşmesini gösterir; scheduled-run
deployment kapısını değiştirmez.

Repair olayları:

- EN-SMA 1, TR-RSI 8, TR-MACD 6: Docker cold-start host timeout;
- TR-MACD 7, 8, 12, 19: modelin saf Python yerine syntax-invalid açıklama /
  Markdown fence içeren yanıt döndürmesi;
- yedi repair'in tamamı ikinci sürümde başarıya ulaştı;
- iki repair gerektiren run olmadı.

### Türkçe / İngilizce karşılaştırması

| Dil | Scheduled | HTTP 200 | First-pass | Repair |
|---|---:|---:|---:|---:|
| EN | 100 | 95 | 94 | 1 |
| TR | 80 | 77 | 71 | 6 |

Provider failure'ları çıkarıldığında EN first-pass 94/95 (%98,95), TR
first-pass 71/77 (%92,21) olmuştur. RSI, SMA ve EMA semantik çiftleri kapıları
geçmiştir. Türkçe MACD, dört prose/fence syntax failure ve bir cold-start timeout
nedeniyle İngilizce eşinden belirgin biçimde daha düşük first-pass güvenilirlik
göstermiştir.

Ana artifacts:

- `reports/strategy-reliability/20260824-210644/post-hardening/summary.json`
- `reports/strategy-reliability/20260824-210644/post-hardening/summary.csv`
- `reports/strategy-reliability/20260824-210644/post-hardening/report.md`
- per-run JSON ve generated sources aynı dizinin `runs/` altındadır.

## Final doğrulama

- `python -m pytest`: **146 passed**.
- Local `llm-strategy-sandbox:dev` image final worker ile rebuild edildi.
- `scripts/check_sandbox.py`: schema v2, sandboxed, success, hash match.
- `scripts/check_canonical_strategies.py`: 7/7 static valid, 7/7 Docker smoke.
- `scripts/check_sandbox_failure_protocol.py`: infinite-loop source worker içinde
  `STRATEGY_TIMEOUT`; bozuk SMA API `STRATEGY_RUNTIME_ERROR` ve allowlisted
  `AttributeError` olarak doğrulandı.
- `scripts/check_nvidia_connection.py`: configured model ile başarılı.
- Final küçük real route matrix: EN-SMA 1/1 ve TR-SMA 1/1 HTTP 200,
  first-pass, sıfır repair (`20260825-005449`).

## Değiştirilen ve eklenen dosyalar

Ana implementation:

- `.env.example`, `README.md`, `app/config.py`
- `app/llm/prompt_builder.py`, `app/llm/prompt_examples.py`
- `app/llm/repair_context.py`, `app/llm/nvidia_client.py`
- `app/runtime/models.py`, `app/runtime/docker_executor.py`
- `sandbox/worker.py`
- `app/services/strategy_service.py`, `app/services/strategy_lab_service.py`
- `app/services/strategy_lab_observer.py`
- `scripts/check_canonical_strategies.py`
- `scripts/check_sandbox_failure_protocol.py`
- `scripts/run_strategy_reliability_matrix.py`

Testler:

- `tests/test_config.py`, `tests/test_docker_executor.py`
- `tests/test_indicator_contract.py`, `tests/test_nvidia_client.py`
- `tests/test_strategy_lab_service.py`, `tests/test_repair_context.py`

Tasarım ve rapor:

- `docs/structured_strategy_v2.md`
- `docs/strategy_lab_hardening_report.md`

Public FastAPI request/response contract ve mobil uygulama değiştirilmemiştir.

## Bilinen sınırlamalar

1. Direct Python generation prompt kurallarına rağmen prose/fence veya başka
   syntax-invalid çıktı üretebilir; Türkçe MACD bunu 4/20 kez gösterdi.
2. NVIDIA availability/latency uygulama tarafından düzeltilemez. Timeout artık
   bounded ve retry görünürdür, fakat provider outage yine HTTP 502 üretir.
3. Static validator izinli bir üçüncü taraf sınıfın tüm method adlarını type-check
   etmez; Docker smoke zorunlu savunma katmanı olmaya devam eder.
4. Final provider/cold-start düzeltmeleri sonrasında tam 180-run matris yeniden
   çalıştırılmadı; yalnız küçük EN/TR SMA real smoke yapıldı.
5. Yahoo Finance community veri kaynağının availability ve veri kalitesi garanti
   edilemez.
6. Endpoint hâlâ uzun süren synchronous request/response modelidir.

## İkinci nesil öneri

`docs/structured_strategy_v2.md`, doğal dil -> strict JSON spec -> semantic
validation -> deterministic compiler -> static validation -> Docker -> backtest
akışını tanımlar. Crossover offset'ini LLM kabul etmez; compiler her crossover'ı
deterministik `[-2]/[-1]` mantığına genişletir. Indicator adapter ve exact method
seçimi trusted template'lerden gelir.

Bu mimari syntax, import, interface, pandas adapter, method-name ve crossover
rastlantısallığını maddi biçimde azaltır. Provider availability ve doğal dil
niyetinin yanlış anlaşılmasını tek başına çözmez. Mevcut Python pipeline stabilize
edilip JSON pipeline feature flag altında shadow matrix ile kanıtlanmadan mevcut
akış kaldırılmamalıdır.
