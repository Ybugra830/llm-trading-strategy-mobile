"""Uygulama yapılandırması."""

from functools import lru_cache
from pathlib import Path

from typing import Annotated

from pydantic import Field, SecretStr, StringConstraints
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
ROOT_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"

SandboxImage = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$",
    ),
]
SandboxMemory = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        to_lower=True,
        pattern=r"^[1-9][0-9]*[mg]$",
    ),
]


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
    sandbox_image: SandboxImage = "llm-strategy-sandbox:dev"
    sandbox_timeout_seconds: float = Field(default=10, ge=1, le=60)
    sandbox_memory: SandboxMemory = "256m"
    sandbox_cpus: float = Field(default=1, gt=0, le=4)
    sandbox_pids_limit: int = Field(default=64, ge=16, le=256)
    sandbox_max_output_bytes: int = Field(
        default=1_048_576,
        ge=4_096,
        le=4_194_304,
    )
    max_strategy_versions: int = Field(default=3, ge=1, le=3)


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
