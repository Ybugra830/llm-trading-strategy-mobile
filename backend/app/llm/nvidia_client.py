"""NVIDIA NIM için OpenAI uyumlu asenkron istemci."""

from openai import AsyncOpenAI, OpenAIError

from app.config import Settings
from app.llm.prompt_builder import build_strategy_messages


class NvidiaNimError(RuntimeError):
    """NVIDIA NIM isteği güvenli biçimde tamamlanamadığında oluşur."""


class NvidiaNimClient:
    """NVIDIA NIM üzerinden strateji kodu üretir."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def model(self) -> str:
        """Yapılandırılmış model adını döndür."""
        return self._settings.nvidia_model

    async def generate_code(self, prompt: str) -> str:
        """Doğal dil strateji isteğini Python koduna dönüştür."""
        api_key = self._settings.nvidia_api_key.get_secret_value().strip()
        if not api_key:
            raise NvidiaNimError("NVIDIA API anahtarı yapılandırılmamış.")

        try:
            async with AsyncOpenAI(
                api_key=api_key,
                base_url=self._settings.nvidia_base_url,
            ) as client:
                completion = await client.chat.completions.create(
                    model=self._settings.nvidia_model,
                    messages=build_strategy_messages(prompt),
                    max_tokens=self._settings.nvidia_max_tokens,
                    temperature=0.1,
                )
        except OpenAIError as exc:
            raise NvidiaNimError("NVIDIA NIM isteği başarısız oldu.") from exc

        if not completion.choices:
            raise NvidiaNimError("NVIDIA NIM boş bir yanıt döndürdü.")

        content = completion.choices[0].message.content
        if not content or not content.strip():
            raise NvidiaNimError("NVIDIA NIM boş bir yanıt döndürdü.")

        return content.strip()
