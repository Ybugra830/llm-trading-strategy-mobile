"""Uygulama yapılandırması."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Ortam değişkenlerinden yüklenen uygulama ayarları."""

    model_config = SettingsConfigDict(
        env_file=(ROOT_ENV_FILE, BACKEND_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    nvidia_api_key: SecretStr = SecretStr("")
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "openai/gpt-oss-20b"
    nvidia_max_tokens: int = Field(default=2048, gt=0)


@lru_cache
def get_settings() -> Settings:
    """Ayarları süreç boyunca yeniden kullanılmak üzere yükle."""
    return Settings()


def get_nvidia_config_summary(settings: Settings) -> dict[str, bool | int | str]:
    """Gizli değeri açığa çıkarmadan NVIDIA yapılandırmasını özetle."""
    api_key = settings.nvidia_api_key.get_secret_value().strip()
    return {
        "api_key_present": bool(api_key),
        "api_key_length": len(api_key),
        "base_url": settings.nvidia_base_url,
        "model": settings.nvidia_model,
        "max_tokens": settings.nvidia_max_tokens,
    }
