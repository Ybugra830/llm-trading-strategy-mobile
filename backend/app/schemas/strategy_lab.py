"""Flutter-facing Strategy Lab request ve response şemaları."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.market.bist_symbols import normalize_bist_symbol
from app.schemas.backtest import BacktestDataSummary, BacktestMetrics
from app.schemas.strategy import StrategyPrompt
from app.schemas.validation import StrategyValidationResponse


class StrategyLabRunRequest(BaseModel):
    """End-to-end Strategy Lab isteği."""

    prompt: StrategyPrompt
    symbol: str = Field(min_length=1, max_length=16)
    initial_cash: float = Field(default=100_000, gt=0, allow_inf_nan=False)
    commission: float = Field(default=0.002, ge=0, lt=0.1, allow_inf_nan=False)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value: object) -> object:
        return normalize_bist_symbol(value) if isinstance(value, str) else value


class StrategyLabGeneration(BaseModel):
    """Üretilen final strateji ve repair metadata'sı."""

    model: str
    attempt_count: int = Field(ge=1, le=3)
    repaired: bool
    code: str

    @model_validator(mode="after")
    def validate_repaired_flag(self) -> "StrategyLabGeneration":
        if self.repaired is not (self.attempt_count > 1):
            raise ValueError("repaired must match attempt_count")
        return self


class StrategyLabRuntime(BaseModel):
    """Public sandbox çalışma özeti."""

    sandboxed: Literal[True] = True
    smoke_test_passed: Literal[True] = True


class StrategyLabConfiguration(BaseModel):
    initial_cash: float
    commission: float


class StrategyLabRunResponse(BaseModel):
    status: Literal["success"] = "success"
    generation: StrategyLabGeneration
    validation: StrategyValidationResponse
    runtime: StrategyLabRuntime
    symbol: str
    yahoo_symbol: str
    data: BacktestDataSummary
    configuration: StrategyLabConfiguration
    metrics: BacktestMetrics


class StrategyLabDefaults(BaseModel):
    initial_cash: float
    commission: float


class StrategyPromptLimits(BaseModel):
    min_length: int
    max_length: int


class StrategyLabCapabilitiesResponse(BaseModel):
    supported_symbols: list[str]
    supported_indicators: list[str]
    defaults: StrategyLabDefaults
    prompt: StrategyPromptLimits
