# Sistem Mimarisi

## Mevcut uygulama

Bu aşamada yalnızca aşağıdaki parçalar vardır:

- Android ve iOS hedefli Flutter uygulama kabuğu
- FastAPI uygulama kabuğu
- `GET /health` sağlık endpoint'i
- Backend ve Flutter testleri
- Türkçe proje dokümantasyonu

Mobil uygulama backend'e bağlanmaz. LLM, piyasa verisi, teknik indikatör,
strateji doğrulama ve backtest işlevleri henüz yoktur.

## Planlanan mimari

```text
Flutter Mobile
      ↓ HTTPS
FastAPI Backend
      ↓
LLM Provider (planlanan: Azure OpenAI)
      ↓
Strateji doğrulama
      ↓
Piyasa verisi
      ↓
Backtest
      ↓
Sonuçların Flutter'a döndürülmesi
```

Planlanan yapıda Flutter kullanıcı arayüzünü sunacak ve backend ile HTTPS
üzerinden iletişim kuracaktır. Sağlayıcı kimlik bilgileri mobil uygulamada
tutulmayacaktır. FastAPI; LLM sağlayıcısı, doğrulama, piyasa verisi ve backtest
süreçlerinin sunucu tarafındaki giriş noktası olacaktır.

Azure OpenAI, `yfinance`, `ta`, `backtesting.py`, Docker, Nginx ve VPS dağıtımı
yalnızca planlanmaktadır; bu aşamada bağımlılık veya uygulama kodu olarak
eklenmemiştir.

## Planlanan güvenlik ilkeleri

- Gizli değerler yalnızca sunucu tarafındaki ortam değişkenlerinde tutulacaktır.
- Gerçek `.env` dosyaları ve API anahtarları Git'e eklenmeyecektir.
- LLM çıktıları güvenilir veya doğrudan çalıştırılabilir kod kabul edilmeyecektir.
- Üretilen kod, çalıştırılmadan önce doğrulama ve güvenlik sınırlarından geçecektir.
