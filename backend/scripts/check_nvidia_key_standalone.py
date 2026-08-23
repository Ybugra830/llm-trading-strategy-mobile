import getpass, os, openai
key = os.getenv("NVIDIA_API_KEY") or getpass.getpass("NVIDIA API key: ")
try:
    result = openai.OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=key, timeout=60, max_retries=0).chat.completions.create(model="meta/llama-3.3-70b-instruct", messages=[{"role": "user", "content": "Merhaba"}], max_tokens=32)
    print("BAŞARILI: Key geçerli ve API kullanım hakkın var." if result.choices[0].message.content else "Key geçerli; ancak model boş yanıt verdi.")
except openai.AuthenticationError:
    print("Key geçersiz.")
except openai.PermissionDeniedError:
    print("Key geçerli olabilir; ancak bu modele erişim iznin yok.")
except openai.RateLimitError as exc:
    text = str(exc).lower()
    print("Kredin bitmiş veya kullanım kotan dolmuş." if any(word in text for word in ("credit", "quota", "balance", "insufficient")) else "Geçici istek hız limitine ulaştın; bu kredi bittiği anlamına gelmez.")
except openai.APIConnectionError:
    print("NVIDIA'ya bağlanılamadı: ağ, DNS, SSL veya timeout sorunu.")
except openai.APIStatusError as exc:
    print(f"NVIDIA sağlayıcı hatası: HTTP {exc.status_code}.")
