"""Host ve izole worker arasındaki katı runtime modelleri."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.backtest import BacktestMetrics
from app.schemas.validation import StrategyValidationResponse

SANDBOX_SCHEMA_VERSION = 1
SandboxStage = Literal["smoke", "backtest"]


class SandboxErrorCode(StrEnum):
    STRATEGY_IMPORT_ERROR = "STRATEGY_IMPORT_ERROR"
    STRATEGY_CLASS_MISSING = "STRATEGY_CLASS_MISSING"
    STRATEGY_INTERFACE_ERROR = "STRATEGY_INTERFACE_ERROR"
    STRATEGY_RUNTIME_ERROR = "STRATEGY_RUNTIME_ERROR"
    STRATEGY_TIMEOUT = "STRATEGY_TIMEOUT"
    STRATEGY_RESOURCE_LIMIT = "STRATEGY_RESOURCE_LIMIT"
    INVALID_SANDBOX_OUTPUT = "INVALID_SANDBOX_OUTPUT"
    SANDBOX_UNAVAILABLE = "SANDBOX_UNAVAILABLE"


class SandboxResult(BaseModel):
    """Worker'ın tek JSON mesajı için versiyonlu sözleşme."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[SANDBOX_SCHEMA_VERSION]
    success: bool
    stage: SandboxStage
    error_code: SandboxErrorCode | None = None
    error_message: str | None = Field(default=None, max_length=300)
    strategy_code_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    metrics: BacktestMetrics | None = None
    duration_seconds: float = Field(ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_success_contract(self) -> "SandboxResult":
        if self.success and (self.error_code is not None or self.error_message is not None):
            raise ValueError("successful sandbox result cannot contain an error")
        if not self.success and self.error_code is None:
            raise ValueError("failed sandbox result requires an error code")
        if self.stage == "backtest" and self.success and self.metrics is None:
            raise ValueError("successful backtest requires metrics")
        return self


@dataclass(frozen=True)
class FrozenStrategy:
    """Smoke sonrasında değiştirilemeyen final strateji sürümü."""

    code: str
    sha256: str
    model: str
    attempt_count: int
    validation: StrategyValidationResponse
