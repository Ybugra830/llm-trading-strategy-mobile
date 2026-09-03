"""Host ve izole worker arasındaki katı runtime modelleri."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator

from app.schemas.backtest import BacktestMetrics
from app.schemas.validation import StrategyValidationResponse

SANDBOX_SCHEMA_VERSION = 3
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


class SafeFailureType(StrEnum):
    ATTRIBUTE_ERROR = "AttributeError"
    TYPE_ERROR = "TypeError"
    VALUE_ERROR = "ValueError"
    INDEX_ERROR = "IndexError"
    KEY_ERROR = "KeyError"
    RUNTIME_ERROR = "RuntimeError"
    ZERO_DIVISION_ERROR = "ZeroDivisionError"
    OVERFLOW_ERROR = "OverflowError"
    UNKNOWN_RUNTIME_ERROR = "UnknownRuntimeError"


class SafeFailureContext(BaseModel):
    """Only fixed vocabulary may cross the sandbox boundary."""

    model_config = ConfigDict(extra="forbid")
    family: Literal["position_management", "indicator_adapter"]
    finding: Literal["invalid_position_attribute", "invalid_trade_attribute", "invalid_indicator_attribute"]
    api: Literal["Position.entry_price", "Position.unsupported_attribute", "Trade.unsupported_attribute", "indicator.unsupported_attribute"]

    @model_validator(mode="after")
    def validate_pair(self) -> "SafeFailureContext":
        allowed = {
            ("position_management", "invalid_position_attribute", "Position.entry_price"),
            ("position_management", "invalid_position_attribute", "Position.unsupported_attribute"),
            ("position_management", "invalid_trade_attribute", "Trade.unsupported_attribute"),
            ("indicator_adapter", "invalid_indicator_attribute", "indicator.unsupported_attribute"),
        }
        if (self.family, self.finding, self.api) not in allowed:
            raise ValueError("inconsistent safe failure context")
        return self


class SandboxResult(BaseModel):
    """Worker'ın tek JSON mesajı için versiyonlu sözleşme."""

    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[SANDBOX_SCHEMA_VERSION]
    success: StrictBool
    stage: SandboxStage
    error_code: SandboxErrorCode | None = None
    error_message: str | None = Field(default=None, max_length=300)
    safe_failure_type: SafeFailureType | None = None
    safe_failure_context: SafeFailureContext | None = None
    strategy_code_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    metrics: BacktestMetrics | None = None
    duration_seconds: float = Field(ge=0, allow_inf_nan=False, strict=True)

    @field_validator("schema_version", mode="before")
    @classmethod
    def validate_schema_version_type(cls, value):
        if type(value) is not int:
            raise ValueError("schema version must be an integer")
        return value

    @model_validator(mode="after")
    def validate_success_contract(self) -> "SandboxResult":
        if self.success and (
            self.error_code is not None
            or self.error_message is not None
            or self.safe_failure_type is not None
            or self.safe_failure_context is not None
        ):
            raise ValueError("successful sandbox result cannot contain an error")
        if not self.success and self.error_code is None:
            raise ValueError("failed sandbox result requires an error code")
        if self.stage == "backtest" and self.success and self.metrics is None:
            raise ValueError("successful backtest requires metrics")
        if (
            not self.success
            and self.error_code == SandboxErrorCode.STRATEGY_RUNTIME_ERROR
            and self.safe_failure_type is None
        ):
            raise ValueError("runtime failure requires a safe failure type")
        if self.safe_failure_context is not None and (
            self.error_code != SandboxErrorCode.STRATEGY_RUNTIME_ERROR
            or self.safe_failure_type != SafeFailureType.ATTRIBUTE_ERROR
        ):
            raise ValueError("safe context requires an AttributeError runtime failure")
        return self


@dataclass(frozen=True)
class FrozenStrategy:
    """Smoke sonrasında değiştirilemeyen final strateji sürümü."""

    code: str
    sha256: str
    model: str
    attempt_count: int
    validation: StrategyValidationResponse
