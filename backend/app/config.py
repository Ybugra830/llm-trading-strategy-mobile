"""Uygulama yapılandırması."""

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ortam değişkenlerinden yüklenen uygulama ayarları."""

    model_config = SettingsConfigDict(
        env_file=".env",
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
