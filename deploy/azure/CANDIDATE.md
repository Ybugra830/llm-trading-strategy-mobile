# Azure 8001 aday hazırlığı

25 Ekim 2026. Çalışma dalı `codex/strategy-lab-release`; dağıtılacak commit bu notu içeren release commit'idir. Main değiştirilmez. Bu aşama yalnız GitHub hazırlığıdır; Azure'da komut çalıştırılmadı, 8000 canlı servisi, Nginx ve frontend değiştirilmedi.

## Yerel kanıt ve kapsam

- Yerelde yüklenen kaynak hash'i `652a7e273a6528f15e978de3a07e02013c18c54422223279bbbd2a2f2a70a48a`; çalışan süreç ile disk eşleşti. Windows CRLF hash'i Linux checkout hash'iyle karıştırılmamalı; Git LF kimliği ayrıca kaydedilir.
- Statik güvenlik düzeltmesinde 12/12 kayıtlı container dosya erişimi kaynağı ve 34 yakın varyant reddedildi. Bunlar yürütülmedi. 12 mock entegrasyonda Docker/veri/backtest sıfırdı. Sekiz kanonik ve 17 arşiv stratejisi statik kontrolden geçti.
- Son tam backend koşusu 961 geçti, 1 opt-in test atlandı. Ayrı terminal Docker grubu 4/4; sekiz güvenli kanonik Docker smoke koşusu başarılıdır. Bunlar tam güvenlik garantisi değildir.
- Yerel araştırmanın 30 HTTP isteği: 17 HTTP 200, 9 HTTP 422, 4 HTTP 502; 17 backtest. Beş desteklenen bağımsız karşılaştırma geçti; üçü işlemli, ikisi sıfır işlemli. Sağlayıcı deneme/retry sayısı ve ham uygunluk ağacı bu grupta gözlenmedi. Geçmiş sonuçlar yeni release üzerinde yeniden çalışmış sayılmaz.
- Kanıtlar yerelde `backend/verification/release-validation/20261024-232736/` ve `backend/verification/security-fix/20261024-235302/` altında korunur; deney arşivleri, gerçek env, özel yedek ve build Git'e eklenmez. Küçük güvenlik ve model yanıtı fixture'ları testlerin parçasıdır; tehlikeli fixture'lar yalnız AST/metin olarak kullanılır.

## Backend ve worker gereksinimleri

Backend systemd + kendi venv'iyle Python >=3.11 kullanır. Bağımlılıklar `backend/pyproject.toml`; yerelde sınanan sürümler openai 2.54.0, httpx 0.28.1, backtesting 0.6.6, ta 0.11.0, pandas 3.0.6, yfinance 1.7.0'dır. Sunucudaki kurulu sürümler henüz doğrulanmadı; yerel Windows venv taşınmaz.

Sandbox build bağlamı `backend/sandbox`; Dockerfile Python 3.11-slim kullanır. Worker ve `requirements.txt` bu tur değişmedi. Mevcut image ancak aday checkout'taki worker SHA-256 ve gereken bağımlılıklarla eşleşirse yeniden kullanılabilir. Yerel image `llm-strategy-sandbox:dev`, ID `sha256:7713f75ff8f2adc3bcc9ad464379402bd16b39cab7cf16fc88afe7eb6cb74cba`, yerel CRLF worker hash'i `8ce7d37783d41199087d2482081da386e71fd165c45e47833d25ec4377a94e5c`. Bunlar Azure image/worker kimliği değildir. Linux LF worker kimliği ayrıca belirtilir. Çalışan eski image silinmez veya etiketi körlemesine değiştirilmez.

Docker ağsız, rootfs salt okunur, non-root 10001:10001, cap-drop ALL, no-new-privileges, bellek/CPU/PID/çıktı ve süre sınırları korunur. Backend kullanıcısının Docker erişimi aday aşamasında sınanır. Terminal emir regresyonu artık arşiv gerektirmeyen küçük sentetik test fixture'ını kullanır.

## Aday ayarları ve frontend

Primary `nvidia/nemotron-3.5-super-vl-120b-a12b`, fallback `minimaxai/minimax-m3.1-flash`, base URL `https://integrate.api.nvidia.com/v1` korunacak. Sunucu env'sinin güvenli yedeği ve ayar kaynağı belirlendikten sonra yalnız gereken alanlar düzenlenir; yerel `.env` bütün olarak taşınmaz. Settings önceliği açık değerler > süreç ortamı > backend env > kök env > varsayılanlardır; önbellek nedeniyle yeni aday süreç gerekir.

Uygunluk toplam 30 sn, üretim/her repair toplam 180 sn; etkin farklı fallback ile primary 15/90 sn, fallback ilk son tarihe kadar kalan süreyi kullanır. SDK retry 0; fallback düzeninde model başına tek HTTP denemesi. Geçerli ret/açıklama, bozuk çıktı ve 400/401/403 geçiş başlatmaz. İlk üretim + en fazla iki repair korunur.

Production frontend `mobile/build/web`; son Flutter analyze ve 59 test ile release build başarılıdır. Mobil kaynak değişmediği için build gereksiz yere tekrarlanmadı. `main.dart.js` SHA-256 `85473d92f7fe74a43cecb4b4df15a477a930057c8c8119b8b5c3414679287a8d`; localhost/Android 8000 URL'si derlenmiş dosyada bulunmuyor. Release web aynı origin ve `/api/` kullanır. Build'de CupertinoIcons font uyarısı vardır. Build henüz sunucuya aktarılmadı.

Repo Nginx şablonunun 360 sn read/send sınırı ve frontend'in 300 sn süresi, bütün repair'ler kullanıldığında olası toplam backend süresinden kısadır. Canlı Nginx yapılandırması incelenmedi; otomatik süre artışı yapılmaz. Aday yanıt süreleri ve bu sınır ayrı kabul konusu olarak korunur. CORS aynı origin release için gerekmeyebilir; aday portu arayüze bağlamadan önce gerçek erişim düzeni belirlenir.

## Sınırlı aday kabulü ve açık kayıtlar

`candidate-acceptance.json` özgün metinleri ve geçmiş olumsuz sonuçları içerir. Bunlar giderilmiş sayılmaz. 30'luk matris tekrarlanmaz; model/prompt değiştirme veya başarısız isteği değişikliksiz tekrar döngüsü yapılmaz.

- Temel kapanış: anlamsız girdi ret ve sıfır downstream; eksik RSI açıklama ve sıfır downstream; tam THYAO RSI zinciri AST/Docker/veri/backtest. HTTP 200 tek başına semantik doğruluk değildir.
- 04: dönem verilmemiş RSI, belgeli 14 varsayılanıyla kabul beklenirken sayısal kanıt hatası. Ham yanıt olmadığı için model/app kök nedeni kesin değil.
- 18: açık RSI14+SMA20 AND/OR kurallarına yanlış açıklama sorusu. Model kararı veya rol çıkarımı ayrımı için yapılandırılmış yanıt gerekir.
- 24: eksik çıkışa çelişkili accepted yanıtı backend tarafından engellendi. Beklenen açıklama yanıtı doğrulanmadı; üretime geçilmedi.
- 26: RSI0 için beklenen invalid_parameters açıklaması yerine sayısal kanıt hatası. Kök neden belirsiz; üretime geçilmedi.
- 11: FROTO kod üretimi/AST/smoke sonrasında market_clean hatası. Ham indirme yok; veri/satır kusuru bilinmiyor. Önce modelsiz bir veri kontrolü düşünülebilir; yeni indirme eski hatanın ham verisi sayılmaz.

04/18/24/26 için gerekirse yalnız uygunluk aşaması; ham hata gövdesi veya headers yerine güvenli yapılandırılmış yanıt, aşama ve istenen/dönen model kaydı tutulur. Bu kayıtlar tek başına Azure altyapı kusuru kanıtı değildir. Desteklenen stratejiler ve veri yolu için kabul eksikleri olarak raporlanır; canlı geçiş onayı verilmiş değildir.

## Manuel sıra ve geri dönüş sınırı

İlk tek adım `discover-candidate.sh` salt okunur keşfidir. Servis/çalışma dizinleri, release commit'leri, worker hash'leri, image kimlikleri ve yedek yolları gösterilir; env, servis içeriği, ham log veya Nginx yapılandırması dökülmez. Çıktı kullanıcıdan gelmeden sunucu değişikliği adımı verilmez.

Önceden bildirilen `/opt/strategy-lab-releases/648d3aa`, `llm-strategy-candidate.service:8001`, `/opt/llm-trading-strategy-mobile`, `llm-strategy.service:8000`, `/var/www/strategy-lab` ve yedekler bugün doğrulanmış değildir. Kesin yedek yolu bilinmiyor. Mevcut aday, image ve yedek uygunsa yeniden kullanılır; eski çalışan sürüm korunur. Keşiften sonra adaya özel env/unit/release/image kimlikleri ve yedekler üzerinden kesin geri dönüş komutları hazırlanır. Bu bilgiler gelmeden uydurma geri dönüş komutu veya 8000/Nginx/frontend geçiş komutu verilmez.
