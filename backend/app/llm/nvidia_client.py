"""NVIDIA NIM için OpenAI uyumlu asenkron istemci."""

import logging
import re
from dataclasses import dataclass

from openai import (
    APIConnectionError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)

from app.config import Settings
from app.llm.prompt_builder import build_strategy_messages

logger = logging.getLogger(__name__)

NVIDIA_PROVIDER_ERRORS = (
    AuthenticationError,
    PermissionDeniedError,
    NotFoundError,
    BadRequestError,
    RateLimitError,
    APIConnectionError,
    APITimeoutError,
    OpenAIError,
)
NVIDIA_API_KEY_PATTERN = re.compile(r"nvapi-[A-Za-z0-9_-]+")


class NvidiaNimError(RuntimeError):
    """NVIDIA NIM isteği güvenli biçimde tamamlanamadığında oluşur."""


@dataclass(frozen=True)
class ProviderErrorDetails:
    """Log ve tanı araçlarında kullanılabilen güvenli sağlayıcı hata özeti."""

    exception_type: str
    status_code: int | None
    request_id: str | None
    message: str

    def as_text(self) -> str:
        """Özeti tek satırlık, okunabilir metne dönüştür."""
        return (
            f"type={self.exception_type} "
            f"status={self.status_code if self.status_code is not None else '-'} "
            f"request_id={self.request_id or '-'} "
            f"message={self.message}"
        )


def get_provider_error_details(
    error: OpenAIError,
    *,
    api_key: str = "",
) -> ProviderErrorDetails:
    """SDK hatasını sırları maskeleyerek güvenli tanı bilgisine dönüştür."""
    message = str(error)
    if api_key:
        message = message.replace(api_key, "[REDACTED]")
    message = NVIDIA_API_KEY_PATTERN.sub("[REDACTED]", message)
    message = " ".join(message.split())[:1000]

    return ProviderErrorDetails(
        exception_type=type(error).__name__,
        status_code=getattr(error, "status_code", None),
        request_id=getattr(error, "request_id", None),
        message=message,
    )


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
            logger.error("NVIDIA NIM request skipped: API key is not configured.")
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
        except NVIDIA_PROVIDER_ERRORS as exc:
            details = get_provider_error_details(exc, api_key=api_key)
            logger.error("NVIDIA NIM request failed: %s", details.as_text())
            raise NvidiaNimError("NVIDIA NIM isteği başarısız oldu.") from exc

        if not completion.choices:
            logger.error("NVIDIA NIM returned a response without choices.")
            raise NvidiaNimError("NVIDIA NIM boş bir yanıt döndürdü.")

        content = completion.choices[0].message.content
        if not content or not content.strip():
            logger.error("NVIDIA NIM returned a response without text content.")
            raise NvidiaNimError("NVIDIA NIM boş bir yanıt döndürdü.")

        return content.strip()
