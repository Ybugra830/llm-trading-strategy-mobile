"""Build the Turkish report from saved, sanitized evidence (no new live load)."""
import json
import math
from pathlib import Path
import statistics
from collections import Counter
from datetime import datetime, timezone

BASE=Path(__file__).parent
E=BASE/'evidence/20260906-public'
def read(name,default=None):
    p=E/name
    return json.loads(p.read_text(encoding='utf-8')) if p.exists() else default
def link(name):return f'[kanıt](evidence/20260906-public/{name})'
def table(headers,rows):
    def cell(v):return str(v).replace('|','/').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |',*['| '+' | '.join(map(cell,row))+' |' for row in rows]])
def seconds(n):return f'{n:.2f}' if isinstance(n,(int,float)) else '—'

runs=[]
for path in E.glob('*.json'):
    data=read(path.name)
    if isinstance(data,dict) and 'passed' in data and 'requests' in data:
        runs.append(data)
runs.sort(key=lambda r:r.get('start_utc',r.get('end_utc','')))
requests=[(r,x) for r in runs for x in r['requests']]
success=[x for _,x in requests if x.get('http_status')==200 and x.get('duration_seconds',999)<300]
failed=[(r,x) for r,x in requests if x.get('http_status')!=200 or x.get('duration_seconds',999)>=300]
basic=[r for r in runs if r['id'].startswith(('E2E-','SYM-','CASH-','COM-'))]
normal=[r['requests'][0]['duration_seconds'] for r in basic if r['passed']]
dur=sorted(normal)
perf={'samples':len(dur),'min':min(dur) if dur else None,'median':statistics.median(dur) if dur else None,'average':statistics.mean(dur) if dur else None,'p90_nearest_rank':dur[math.ceil(.9*len(dur))-1] if dur else None,'max':max(dur) if dur else None}
fuzz=read('fuzz-ui.json',[]);schema=read('schema.json',[])
ledger=(E/'live-posts.jsonl').read_text(encoding='utf-8').splitlines()
timeouts=read('NET-TIMEOUT.json',{})
abort=read('abort-matrix.json',[])
view=read('viewports.json',[])
caps=read('capabilities.json',{})
azure=read('final-azure.json',read('post-basic-azure.json',{}))
public=read('final-public.json',[])
resources=[json.loads(x) for x in (E/'resources.jsonl').read_text().splitlines()]
available=[];cpu=[];containers=[]
for row in resources:
    lines=row['summary'].splitlines()
    for line in lines:
        if line.startswith('Mem:'):available.append(int(line.split()[-1]))
        fields=line.split()
        if len(fields)>=17 and all(x.isdigit() for x in fields[:17]):cpu.append(100-int(fields[14]))
    containers.append(sum(line.startswith('strategy-sandbox-') and 'Up' in line for line in lines))
phase_rows=[
 (0,'Başlangıç','PASS','Temiz c0ed5ac; Flutter 3.35.5/Dart 3.9.2; başlangıç analyze temiz, 25 Flutter ve 622 backend testi geçti.'),
 (1,'Public smoke','PASS','Ana sayfa/health/capabilities 200; THYAO, 100000 ve %0.20; gerçek Chrome formu.'),
 (2,'A–G stratejileri','PASS','7/7 gerçek UI koşusu başarılı.'),
 (3,'12 sembol','FAIL','İlk matriste TUPRS ve KCHOL HTTP 502; diğer 10 sembol başarılı.'),
 (4,'Sermaye','PASS','100000 / 250000 / 50000 gerçek payload ve response configuration eşleşiyor.'),
 (5,'Komisyon','PASS','%0 / %0.05 / %0.20 / %0.50 dönüşümleri eşleşiyor.'),
 (6,'Prompt sınırları','PASS','10 UI ve 10 schema vakası; uzun giriş UI’da 2000’e kırpılıyor, schema doğrudan fazla uzunluğu reddediyor.'),
 (7,'Belirsiz/lookahead/güvenlik','FAIL','4 güvenli canlı istem başarılı; 9 tehlikeli istem canlıda bilinçli engellendi. Statik alias açığı doğrulandı.'),
 (8,'Sayı fuzz','FAIL','Negatif ve bilimsel gösterim sessizce başka pozitif sayıya dönüşüyor.'),
 (9,'2/5/10 tıklama','PASS','Her biri bir POST ve HTTP 200; yerel controller eşzamanlılık kontrolü de geçti.'),
 (10,'Refresh/abort','NOT TESTABLE','Sunucu öncesi kesilen UI iptal vakaları ayrı kaydedildi; gerçek çalışan sunucu işinin iptal edildiği kanıtlanmadı.'),
 (11,'Ağ/timeout','PASS' if timeouts.get('observed_error_seconds') and read('NET-LATENCY.json',{}).get('passed') else 'NOT TESTABLE','Offline hata + toparlanma, Slow/Fast 3G ve yüksek gecikme. 300 saniyelik frontend timeout sunucu öncesi geciktirmeyle sınandı; gerçek upstream kopuşu ayrı sınırlama.'),
 (12,'14 çözünürlük','PASS' if len(view)==14 else 'NOT TESTABLE','Gerçek fontlarla 14×5 yerel durum ve public ekran görüntüleri; temsilî görüntüler görsel kontrol edildi.'),
 (13,'Mobil benzeri / fiziksel','NOT TESTABLE','Chrome touch ve portrait/landscape emülasyonu; PHYSICAL PHONE NOT VERIFIED. Gerçek mobil klavye doğrulanmadı.'),
 (14,'Sonuç gezinmesi','NOT TESTABLE','In-app Back, yenileme, direct base URL ve yeni bağımsız sekme kontrol edildi; gerçek duplicate tab/result deep-link kapsamı tamamlanmadı.'),
 (15,'2/3 eşzamanlı kullanıcı','PASS' if all(read(f'CONCURRENT-{n}.json',{}).get('passed') for n in [2,3]) else 'FAIL','Beş istek; bağımsız browser context; sembol eşleşmesi ve kaynak örnekleri.'),
 (16,'Performans','PASS' if len(dur)>=10 else 'NOT TESTABLE','Normal başarılı koşular yeniden kullanıldı. Aşama süreleri ayrı ölçülemedi.'),
 (17,'Console/network','PASS','Same-origin API URL doğrulandı; kontrollü offline/fuzz hataları normal E2E hatalarından ayrıldı.'),
 (18,'Secret/static security','FAIL','Public tarama secret_found=false; buna rağmen canlı validator SHA eşleşmeli HIGH alias açığı var.'),
 (19,'Azure/loglar','PASS','Salt okunur systemd/nginx/kernel kontrolü; kesin request ID olmayan aşama korelasyonu yapılmadı.'),
 (20,'WhatsApp / gerçek telefon','NOT TESTABLE','NOT TESTABLE AUTOMATICALLY. Doğrulanmış kendi/test sohbeti ve fiziksel cihaz yok; mesaj gönderilmedi.'),
 (21,'Son regresyon','FAIL','Uygulama değiştirilmedi; yeni acceptance testleri mevcut hataları kırmızı olarak gösteriyor. Son komut sonuçları aşağıda.'),
]
counts=Counter(r[2] for r in phase_rows)
out=[]
def add(text):out.append(text.strip())
add(f'''# Production Demo QA / Stres / Edge-Case Raporu

Çalışma: `20260906-public` · Oluşturulma: {datetime.now(timezone.utc).isoformat()} · Karar: **NO-GO**

## Executive summary

Canlı sürümle birebir eşleşen statik doğrulayıcıda **HIGH filesystem alias açığı** var. Bu kapanmadan GO verilmez. Ek olarak sayı girişi anlamını değiştiren UI hatası ve TUPRS fiyat verisini makine hassasiyeti farkı nedeniyle reddeden temizleyici doğrulandı. Uygulama/deployment düzeltmesi yapılmadı.

22 faz düzeyinde: **{counts['PASS']} PASS / {counts['FAIL']} FAIL / {counts['NOT TESTABLE']} NOT TESTABLE**. Bu sayılar faz sayısıdır; alt vakalar ve test suite sayıları aşağıda ayrı verilmiştir. Bir fazdaki PASS, açıkça belirtilen fiziksel/upstream sınırlamalarının test edildiği anlamına gelmez.

- Canlı backend’e giden kayıtlı sonuçlar: **{len(requests)}**; {len(success)} HTTP 200 ve 300 saniye altında, {len(failed)} başarısız/timeout.
- Tüm POST girişimi bütçesi: **{len(ledger)}/80**; sunucu öncesi kesilen fuzz/timeout/abort ve offline girişimler dahildir. GET ve schema testleri bu sayıya dahil değildir.
- İlk temel matris: 23 koşu, 21 başarı, 2 piyasa-verisi 502. A–G: 7/7; ilk sembol matrisi: 10/12.
- Güvenlik: 12 konteyner/listeden-sözlükten alias regresyonu ve 1 sahte servis-gate regresyonu FAIL. **Hiçbir dosya erişim payload’ı çalıştırılmadı.**
- CRITICAL: 0 doğrulandı; HIGH: 1; MEDIUM: 2; LOW: 0. INFO ve test sınırlamaları ayrıca listelendi. “0 doğrulandı”, yokluğun ispatı değildir.

## Değişiklik ve güvenlik sınırları

Yalnız `qa/` test yardımcıları, temizlenmiş kanıtlar/font fixture’ları ve `mobile/test/production_demo_qa_test.dart` eklendi. Uygulama kaynakları, Docker, worker, Nginx/systemd, `.env`, anahtarlar değiştirilmedi. Servis restart, konteyner zorla silme, host execution fallback, commit/push yapılmadı. Port 8000 hâlâ yalnız `127.0.0.1` üzerinde.

Başlangıç local/Azure commit: `c0ed5ac5f59fa55814145dd89ecae822bead77fe`. Validator SHA-256: `28e2ef246d7abbe2a7a6afd1605b9b2e0b679708f0a113c94c452239b1acbde0`; remote eşleşmesi: **{azure.get('remote_validator_matches')}**. Başlangıç Flutter 3.35.5, Dart 3.9.2; analyze temiz, Flutter 25/25, backend 622/622 (ilk koşuda yalnız pytest cache yazma izni uyarısı).

Public hedef: [Strategy Lab](http://strategy-lab.denmarkeast.cloudapp.azure.com). {link('interim-azure.json')} · {link('final-azure.json')} · {link('browser-version.json')}

## Faz matrisi
''')
add(table(['Faz','Kapsam','Sonuç','Açıklama'],phase_rows))
add('## Gerçek strateji, sembol ve parametre sonuçları\n\nHer satır public Chrome UI’dan üretilmiş gerçek istektir. Başlangıç/bitiş UTC, request body, süre, HTTP, response configuration/metrics/validation, model/repair ve kaynak hash’i bağlantıdaki JSON’dadır. Screen capture dosyaları aynı ID’nin `-input`, `-loading`, `-result.png` dosyalarıdır.')
add(table(['ID','Symbol','Cash','Commission (decimal)','HTTP','Süre (s)','Attempt / repair','Sonuç'],[
 [r['id'],x.get('body',{}).get('symbol'),x.get('body',{}).get('initial_cash'),x.get('body',{}).get('commission'),x.get('http_status'),seconds(x.get('duration_seconds')),str(x.get('generation',{}).get('attempt_count','—'))+' / '+str(x.get('generation',{}).get('repaired','—')),('PASS' if x.get('http_status')==200 and x.get('duration_seconds',999)<300 else 'FAIL')+' '+link(r['id']+'.json')]
 for r,x in requests]))
add('### İlk sembol matrisi\n\nCapabilities dinamik olarak okunmuştur. THYAO için E2E-A yeniden kullanılır; diğer 11 sembol ayrı koşudur. Başarılı yanıtların sembolleri gönderilen sembollerle eşleşmiştir. Başarısız yanıt için “sonuç eşleşti” denmez.')
add(table(['Symbol','Test','İlk durum'],[[s,'E2E-A' if s=='THYAO' else 'SYM-'+s, 'FAIL (502)' if s in ['TUPRS','KCHOL'] else 'PASS'] for s in caps.get('supported_symbols',[])]))
add('### Sermaye / komisyon yorum sınırı\n\n100000, 250000 ve 50000 değerleri request body ve response configuration’da doğrulandı. %0.20 → 0.002; %0.05 → 0.0005. Kaynak hash’i ve veri aralığı kayıtlıdır. Farklı LLM üretimleri nedeniyle salt kâr farkından komisyon/sermaye bug’ı çıkarılmadı. Aynı prompt, aynı kaynak kodu anlamına gelmez; kontrollü ekonomik karşılaştırma bu çalışmada yapılmadı.')
add('## Girdi sınırları ve fuzz\n\nUI matrisi gerçek public arayüzde çalıştırıldı; oluşan POST’lar Chrome Fetch ile **sunucu öncesinde kesildi**. Bu satırlar NVIDIA/backend E2E başarısı değildir. Ayrı yerel Pydantic matrisi backend sözleşmesini doğrular. Kesilen isteklerin kullanıcıya ağ hatası vermesi enjekte edilen koşulun beklenen sonucudur.')
bad={'FUZZ-CASH-2','FUZZ-CASH-3','FUZZ-CASH-9','FUZZ-COM-1'}
def payload_cell(r):
    bodies=[x.get('body',{}) for x in r['requests']]
    if not bodies:return 'POST yok'
    body=bodies[0]
    if r['field_index']==0:return f"prompt uzunluğu={len(body.get('prompt',''))}"
    return str(body.get('initial_cash' if r['field_index']==1 else 'commission'))
add(table(['ID','Girdi','POST','Gönderilen alan','Sonuç'],[[r['id'],repr(r['input']),r['intercepted_post_count'],payload_cell(r),'FAIL' if r['id'] in bad else 'PASS'] for r in fuzz]))
add(link('fuzz-ui.json')+' · '+link('schema.json')+'\n\nBackend schema: commission satırları yüzde değil **decimal** değerlerdir. `NaN`/`Infinity` iki sayısal alanda reddedilir; ilk sermaye >0, komisyon [0,0.1), prompt trim sonrası 5–2000. Çok büyük sonlu sayılarda IEEE-754 hassasiyet sınırı vardır; üst sermaye sınırı mevcut sözleşmede tanımlı değildir.')
add(table(['Schema ID','Alan','Girdi','Kabul','Normalize / hata'],[[r['id'],r['field'],repr(r['input']),r['accepted'],r.get('normalized',r.get('errors'))] for r in schema]))
add('''## Güvenlik bulgusu QA-SEC-01 — HIGH

**Tekrar:** `qa/test_security_regressions.py` içindeki kaynak metinlerini yalnız `ValidationService.validate` ile inceleyin:

```python
import pandas as pd
box = [pd]  # dict karşılığı da aynı sonucu veriyor
box[0].read_csv("qa-not-executed")
```

**Expected:** Kaynak statik aşamada reddedilir; smoke, market ve backtest çağrıları sıfırdır.

**Actual:** pandas `read_csv/read_json/read_pickle/read_excel` ve NumPy `load/save`, liste/sözlük üzerinden geçirildiğinde tam pipeline `valid=True, security_valid=True, errors=[]` döndürüyor. Sahte servis testinde kod smoke girişine ulaşıyor; tripwire burada exception atıyor, kaynak **çalıştırılmıyor**. Direct/normal alias kontrolleri ve doğrudan yasak sürümlerin repair exhaustion testi geçiyor.

**Kök neden:** `backend/app/validators/security_validator.py::_Bindings.origins` liste/sözlük değerlerinin kökenini taşımıyor; `Subscript` çözümlemesi boş kökenle sonuçlanıyor. `_forbidden_origin` bilinmeyen kökeni tehlikeli olarak sınıflandırmadığı için fail-open davranış oluşuyor. `ValidationService.prepare` → `validate_strategy_code` → `validate_security` → `StrategyLabService.run` smoke sınırı etkileniyor.

**Etki:** Generated strategy dosya erişimi yasağı Docker öncesinde garanti edilemiyor. Bu test host/Docker kaçışı veya gerçek veri sızıntısı ispatı değildir; Docker savunmaları yerinde bırakıldı. Canlı validator hash’i eşleştiği için bulgu deploy edilen kod için geçerlidir.

**Öneri:** Konteyner elemanlarının provenance’ını ve belirsiz erişimleri muhafazakâr çözümleyin; yeni acceptance testlerini yeşile çevirin, normal pandas/NumPy pozitif kontrollerini koruyun. Uygulama değişikliği yapılmadı.
''')
add(link('security-regressions.txt')+'\n\n**Canlı çalıştırılmayan 9 istem:** `/etc/passwd` okuma, `open`, `pandas.read_csv`, `numpy.load`, `pathlib.Path.read_text`, `os` ile filesystem inceleme, `__import__`, `/tmp/result.csv` yazma, dış URL’ye veri gönderme. Her biri **NOT TESTABLE — known security blocker**. İstemleri modele göndermek dahi denenmedi.')
add('''## Sayı girişi bulgusu QA-UI-01 — MEDIUM

**Tekrar:** Geçerli RSI promptu ile Initial Capital alanına `-1`, `-100000` veya `1e10`; Commission alanına `-1` yapıştırın ve Run’a basın.

**Expected:** Geçersiz değer açıkça reddedilmeli; bilimsel gösterim destekleniyorsa doğru değer gönderilmeli, desteklenmiyorsa reddedilmelidir.

**Actual:** Sırasıyla cash `1`, `100000`, `110`; commission `0.01` gönderiliyor. UI ve dört yeni widget acceptance testiyle doğrulandı. Tehlikeli/bozuk fuzz istekleri sunucu öncesinde durduruldu.

**Kök neden:** `mobile/lib/app/features/strategy_lab/widgets/strategy_form_fields.dart` içindeki `[0-9.,]` karakter filtresi eksi ve `e` işaretlerini silerek girdinin anlamını değiştiriyor. Controller yalnız filtrelenmiş pozitif sayıyı görüyor; backend de geçerli ama yanlış değeri reddedemez.

**Öneri:** Yapıştırılan sayının tamamını doğrulayın; işaret/üs karakterlerini silip başka sayıya dönüştürmeyin. UI ve controller’da sonlu sayı kontrolünü koruyun/ekleyin. İlgili controller/parser ve widget testleriyle düzeltmeyi doğrulayın.
''')
add(link('fuzz-ui.json')+' · '+link('FUZZ-CASH-2.png')+' · '+link('FUZZ-CASH-9.png')+' · '+link('flutter-test.txt'))
add('''## Piyasa verisi bulgusu QA-DATA-01 — MEDIUM

**Tekrar:** TUPRS / basit RSI / 100000 / %0.20 public koşusunu açın. Ardından `qa/market_probe.py` ile mevcut Azure provider/cleaner karşılaştırmasını inceleyin.

**Expected:** Makine yuvarlama seviyesindeki düzeltilmiş OHLC farkı bütün sembolü kullanılmaz yapmamalı; gerçekten tutarsız fiyatlar reddedilmeye devam etmelidir.

**Actual:** İlk TUPRS koşusu HTTP 502 ve güvenli “Piyasa verisi şu anda kullanılamıyor.” mesajı verdi. Provider 754 satır getiriyor; iki satırda `Close-Low` en az `-1.4210854715202004e-14`. Cleaner `InvalidMarketDataError` üretiyor. Sentetik `np.nextafter(100, +∞)` regresyonu aynı sınırı gösterir.

**Kök neden:** `backend/app/market/ohlcv_cleaner.py::_validate_price_structure` düzeltilmiş float fiyatlarını sıfır toleranslı karşılaştırıyor. `YahooFinanceProvider` `auto_adjust=True` kullanıyor. Bu, NVIDIA/LLM veya Docker altyapı hatası değil.

**Öneri:** Çok dar, ölçekle uyumlu sayısal tolerans/normalizasyon tasarlayın; maddi OHLC tutarsızlıklarının reddini testle koruyun. Genel veri kontrolünü kaldırmayın.

KCHOL ilk koşuda aynı public 502 sınıfına girdi; sonraki doğrudan provider/cleaner tanılaması geçti. Aynı kök neden KCHOL’e tahminle atanmadı; ilk hata geçici/ayrıştırılamayan piyasa-verisi hatası olarak kayıtlıdır.
''')
add(link('market-diagnostic.json')+' · '+link('SYM-TUPRS.json')+' · '+link('SYM-KCHOL.json')+' · '+link('security-regressions.txt'))
add('## Ekran, cihaz ve gezinme\n\nPublic form/dropdown görüntüleri ve yerel beş durum matrisi:')
add(table(['Boyut','Form','Dropdown','Loading','Result','Error'],[[f'{w}×{h}',*[link(f'VIEW-{w}x{h}-{state}.png') if (E/f'VIEW-{w}x{h}-{state}.png').exists() else 'NOT TESTABLE' for state in ['form','dropdown','loading','result','error']]] for w,h in [(r['viewport'][0],r['viewport'][1]) for r in view]]))
add('''Gerçek public fontlarla 14 çözünürlükte form/modal/loading/result/error widget testleri geçti. İlk Ahem placeholder fontu ile görülen altı taşma test altyapısı kaynaklıydı; gerçek Inter/Geist fixture’larıyla kayboldu ve bug sayılmadı. Public screenshot’larda küçük ekran scroll konumu nedeniyle üst başlığın bir kısmının viewport dışına çıkması tek başına clipping bug’ı değildir.

Chrome headless/device emülasyonu fiziksel telefon değildir. `PHYSICAL PHONE NOT VERIFIED`; gerçek mobil klavye ve WhatsApp kendi/test sohbeti `NOT TESTABLE AUTOMATICALLY`. Touch olayları timeout senaryosunda açıkça dispatch edildi; klavye metni otomasyonla girildi. CSS belge overflow kontrolü canvas içi taşmanın yokluğunu tek başına ispatlamaz; widget kontrolleri ve screenshot’larla birlikte değerlendirildi.

Result state bellek tabanlıdır: in-app Back forma döner, base URL yenilemesi/yeni oturum formu açar. Sonucun yeni sekmede kalıcı olması veya shareable result deep-link bu çalışmada doğrulanmadı. Gerçek browser Duplicate Tab komutu test edilmedi.
''')
add(link('navigation.json')+' · '+link('viewports.json')+' · '+link('flutter-qa.txt'))
add('## İptal ve ağ\n\nF5/Ctrl+R için CDP reload eşdeğeri kullanıldı; fiziksel kısayol tuşlarına basılmış gibi raporlanmaz. Abort matrisi sunucu öncesi intercept kullanır; backend iş sonlanması/orphan yokluğu buradan çıkarılmaz.')
add(table(['ID','Kesilen POST','Forma dönüş','Ortam'],[[r['id'],r['intercepted_requests'],r['recovered_form'],r['target']] for r in abort]))
add(f"{link('abort-matrix.json')}\n\nOffline hata ekranı: {link('NET-OFFLINE.json')}. Yeniden bağlantı ve yeni Run sonucu: {link('NET-RECOVER.json')}. Slow 3G=2000 ms/50000 B/s, Fast 3G=562 ms/180000 B/s, latency=3000 ms/1000000 B/s CDP ayarları; fiziksel ağ ölçümü değildir.\n\nFrontend timeout gözlenen hata süresi: **{seconds(timeouts.get('observed_error_seconds'))} saniye**. {link('NET-TIMEOUT.json')} İstek browser içinde bekletildi; backend/NVIDIA işi başlamadı. Kaynaktaki `ApiConfig.runTimeout=5 dakika` ve yerel test ayrıca doğrulandı. Gerçek sunucuya ulaşmış isteğin bağlantı kaybında ne zaman bittiği **NOT TESTABLE**; servis loglarında request-id/aşama sonu korelasyonu yeterli değil.")
add('## Eşzamanlılık ve performans')
add(table(['Ölçü','Değer'],[[k,seconds(v) if k!='samples' else v] for k,v in perf.items()]))
add(f"Örnekler: ilk temel matrisin {len(normal)} başarılı normal koşusu; p90 nearest-rank yöntemiyle hesaplandı. İki başarısız ilk koşu ortalamaya katılmadı; başarısızlıklar ayrı tabloda. 300 saniye üstü başarılı sayılmadı. Ağ enjeksiyonu, belirsiz prompt, concurrency ve browser preflight yükleme süreleri bu normal istatistiğe karıştırılmadı.\n\n2 context: {link('CONCURRENT-2.json')}; 3 context: {link('CONCURRENT-3.json')}. Yanıt sembolleri request sembolleriyle karşılaştırıldı; karışma görülmedi.\n\nLLM / repair / smoke / market / backtest aşama süreleri: **NOT TESTABLE ayrı ayrı**. Response `attempt_count/repaired` bilgisi mevcut; aşama zamanları uydurulmadı. Eşzamanlı log olaylarına kesin request-id yoksa sembol/hash tahminle atanmadı.")
add(f"## Azure, console/network ve secret taraması\n\nVM: 2 vCPU, yaklaşık 3.86 GiB RAM; Docker 29.8.0. {len(resources)} kaynak örneği: kullanılabilir RAM min **{min(available) if available else '—'} MiB**, max **{max(available) if available else '—'} MiB**; örneklenen VM meşgul CPU max **{max(cpu) if cpu else '—'}%** (iowait dahildir). Görülen eşzamanlı container üst değeri **{max(containers) if containers else '—'}**; bu örnekleme gerçek anlık tepeyi garanti etmez. {link('resources.jsonl')}\n\nNRestarts/OOM kontrolünde olay görülmedi; servisler son kontrolde aktif. Geçici çalışan sandbox otomatik orphan sayılmadı. Beklenmeyen servis restart, OOM veya 429 güvenlik kapısı tetiklenmedi. CPU/RAM ve health aralıklarla örneklendi; sürekli telemetri değildir.\n\n{link('final-log-summary.json')} temizlenmiş systemd/nginx/kernel kayıtlarıdır. Tüm logların ham gövdeleri saklanmadı. 502 vakaları request zamanı ve endpoint ile ilişkilendirildi; response market-data sınıfını gösteriyor. KCHOL’in ilk ayrıntılı upstream nedeni belirlenemedi. Test öncesi eski loglar sonuçlara atanmadı.\n\nPublic `/health` tam `{{\"status\":\"ok\"}}`; capabilities JSON, ana sayfa 200. API istekleri same-origin `/api/v1/strategy-lab/run`. Beklenen kesintilerde Chrome network error görülür; bunlar normal koşu console bug’ı sayılmadı. 404 asset, yanlış localhost/127.0.0.1/10.0.2.2 API hedefi veya normal E2E’de uncaught exception doğrulanmadı.\n\nPublic HTML, `main.dart.js`, bootstrap, health/capabilities ve canlı sonuçlarda tanınan credential/private-key örüntüsü taraması: **secret_found=false**. Bu örüntü taramasıdır; bilinmeyen her secret formatının yokluğuna mutlak garanti değildir. Kütüphane `Authorization/Bearer` sabiti tek başına sızıntı sayılmadı. `.env` ve anahtar içeriği okunmadı. {link('final-public.json')}")
add('''### INFO: Soğuk sayfa açılışı ve gözlemlenebilirlik

Public `main.dart.js` yaklaşık 6.45 MB. Bağımsız Chrome context kanıtlarında aynı dosya için yaklaşık 12.9 / 51.2 / 25.7 saniyelik indirmeler görülür; cache hit’ler çok daha hızlıdır. Bunlar bu test makinesinin gerçek ağ ölçümleridir, Azure CPU süresi değildir. İlk açılış maliyetini azaltmak için compression/cache/bootstrap yükleme göstergesi ayrıca değerlendirilebilir; deployment değiştirilmedi. Aşama bazlı request-id ve timing eksikliği başarısızlık/iptal kök nedenini ayırmayı sınırlar.
''')
add('## Son regresyon ve teslim')
add(table(['Komut','Exit','Süre (s)','Kanıt'],[[name,read(name+'.json',{}).get('exit_code','NOT TESTABLE'),seconds(read(name+'.json',{}).get('duration_seconds')),link(name+'.txt')] for name in ['flutter-analyze','flutter-test','backend-pytest','security-regressions']]))
add('''Beklenen ayrım: mevcut backend suite ile yeni QA acceptance suite aynı şey değildir. Yeni testlerin kırmızı olması çalışma sırasında uygulamanın bozulması değil, mevcut eksik güvenlik/sayı/fiyat davranışının kanıtıdır. Hiçbiri xfail/skip ile başarılıya çevrilmedi. Nihai kesin sayılar yukarıdaki komut çıktılarındadır.

## Önerilen değişiklikler — test sonuçlarından ayrı

1. **Önce HIGH:** `backend/app/validators/security_validator.py` konteyner/subscript provenance ve fail-closed davranışı; `backend/tests/test_validation_pipeline.py`, `backend/tests/test_strategy_lab_service.py` regresyonları. Docker ve host fallback kuralları korunmalı.
2. `mobile/lib/app/features/strategy_lab/widgets/strategy_form_fields.dart` sayı filtresi; gerekirse controller/parser sonlu sayı doğrulaması. Yeni dört widget regresyonu ve backend sınır kontrolleri birlikte yeşil olmalı.
3. `backend/app/market/ohlcv_cleaner.py` çok dar sayısal tolerans; gerçek bozuk OHLC reddini koruyan piyasa veri testleri.
4. Ayrı iyileştirme olarak güvenli request-id/aşama timing ve public asset yükleme performansı. Mevcut telemetry olmadan iptal edilen sunucu işinin tamamlandığı iddia edilmemeli.

**Hocaya gönderme kararı: NO-GO.** HIGH filesystem engeli kapanmalı; düzeltmelerden sonra bu testler ve mevcut full suite tekrar çalıştırılmalı. Fiziksel telefon/klavye ve doğrulanmış kendi WhatsApp sohbeti kontrolleri ayrıca manuel yapılmalı.
''')
(BASE/'production-demo-qa-report.md').write_text('\n\n'.join(out)+'\n',encoding='utf-8')
(E/'report-summary.json').write_text(json.dumps({'phase_counts':counts,'live_post_attempts':len(ledger),'completed_backend_responses':len(requests),'successful_backend_responses':len(success),'failed_backend_responses':len(failed),'performance':perf},indent=2),encoding='utf-8')
print(json.dumps({'report':str(BASE/'production-demo-qa-report.md'),'phase_counts':counts,'ledger':len(ledger)}))
