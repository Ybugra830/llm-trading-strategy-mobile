# Production demo QA

Bu klasör uygulama davranışını değiştirmez. `production-demo-qa-report.md` gerçek
sonuçları ve sınırlamaları açıklar. Kanıtlar `evidence/20260906-public/` altındadır.

## Yerel tekrar

```powershell
.\backend\.venv\Scripts\python.exe qa/local_schema_probe.py
.\backend\.venv\Scripts\python.exe -m pytest qa/test_security_regressions.py qa/test_market_regressions.py -p no:cacheprovider
.\backend\.venv\Scripts\python.exe qa/run_local_checks.py widgets
```

Yeni güvenlik, fiyat hassasiyeti ve sayı girişi acceptance testleri mevcut
uygulamadaki açıkları göstermek için **bilerek kırmızıdır**; `xfail` ile gizlenmez.
Backend'in mevcut testleri ayrıca backend çalışma dizininde çalıştırılır.
Üretilen Python kaynakları hiçbir QA güvenlik testinde çalıştırılmaz. Sahte smoke
kapısı yalnız bir tripwire'dır; Docker, piyasa verisi veya backtest başlatamaz.

Widget testleri public uygulamayla eşleşen iki font fixture'ını kullanır;
SHA-256 ve OFL lisansları `fixtures/fonts/` içindedir. Uygulamanın test fontu
Ahem'le oluşan yalancı taşmalar üretim hatası olarak sayılmamıştır.

## Canlı yardımcılar

`qa_driver.py` yalnız açıkça başlatılan fazı çalıştırır. Ayrı Chrome profili ve
localhost CDP portu kullanır; Chrome sandbox'ını kapatmaz. `basic`, `behavior`,
`concurrency`, `network`, `retest` gerçek sağlayıcı maliyeti oluşturabilir.
`fuzz`, `timeout`, `abort` POST'ları sunucu öncesinde durdurur; bu sonuçlar
sunucu tarafı iptal/timeout testi olarak sunulmaz. `views` strateji çalıştırmaz.

`live-posts.jsonl` başarısız, offline ve kesilen girişimleri de bütçeye sayar.
Bu çalıştırmaya ait toplam 80 sınırı sıfırlanmaz. Yeni bir çalışma için ayrı
run-id, yeni açık bütçe ve yeniden sağlık kontrolü gerekir; yardımcıları körlemesine
art arda tekrar çalıştırmayın. Aynı anda iki canlı yardımcı başlatmayın.

`remote_audit.py` yalnız servis/kod uyumu, public varlıklar ve izinli log alanlarını
kaydeder. Ham HAR, ham journal, header, `.env` veya anahtar içeriği saklamaz.
`market_probe.py` yalnız mevcut sağlayıcının piyasa verisini ve temizleyicisini
karşılaştırır; LLM ve strateji yürütmez. Hiçbiri servisleri yeniden başlatmaz,
deployment değiştirmez veya commit/push yapmaz.
