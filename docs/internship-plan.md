# Staj Projesi Geliştirme Planı

## 1. Proje iskeleti

- Backend, mobile ve dokümantasyon sınırlarını oluşturma
- FastAPI sağlık endpoint'i ve temel test
- Android/iOS Flutter başlangıç ekranı ve widget testi
- Depo temizliği ve secrets koruması

## 2. API sözleşmesi ve veri modelleri

- Strateji isteği ve sonuç modellerini tanımlama
- Girdi doğrulama ve tutarlı hata yanıtları
- Mobile-backend iletişim sözleşmesini belgeleme

## 3. Piyasa verisi ve teknik analiz

- `yfinance` veri erişim katmanı
- Veri temizleme ve tarih aralığı doğrulama
- `ta` ile kontrollü indikatör hesaplama
- Birim testleri ve hata senaryoları

## 4. Azure OpenAI entegrasyonu

- Sunucu tarafı yapılandırma ve secrets yönetimi
- Yapılandırılmış strateji çıktısı
- LLM çıktısı doğrulama ve güvenlik sınırları
- Başarısızlık ve yeniden deneme davranışları

## 5. Backtest

- Doğrulanmış stratejiyi `backtesting.py` ile çalıştırma
- Performans metrikleri ve sonuç modeli
- Tekrarlanabilir test verileri ve senaryolar

## 6. Mobile deneyimi

- Strateji oluşturma formu
- Yükleniyor, hata ve boş durum ekranları
- Backtest özet ve detay görünümleri
- Backend entegrasyon testleri

## 7. Dağıtım ve teslim

- Backend Docker imajı
- Nginx ters proxy ve HTTPS hazırlığı
- Ubuntu VPS kurulum dokümantasyonu
- Son testler, izleme ve proje sunumu

Her aşama küçük, test edilebilir teslimlere ayrılacak; bir sonraki aşamaya
geçmeden önce ilgili dokümantasyon ve testler güncellenecektir.
