# Backend

Bu dizin, projenin Python 3.11+ ve FastAPI tabanlı backend uygulamasıdır.
Mevcut aşamada sağlık kontrolü ve NVIDIA NIM üzerinden Python strateji kodu
üretme endpoint'i bulunur.

> Üretilen kod henüz doğrulanmaz veya çalıştırılmaz. AST doğrulaması, güvenli
> yürütme ve backtest sonraki aşamalarda geliştirilecektir.

## Kurulum

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Yerel `.env` dosyasındaki `NVIDIA_API_KEY` değerini kendi NVIDIA API
anahtarınızla doldurun. Gerçek anahtarı Git'e eklemeyin.

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

## Test

```powershell
pytest
```

Testler gerçek NVIDIA API anahtarı veya dış ağ bağlantısı kullanmaz.
