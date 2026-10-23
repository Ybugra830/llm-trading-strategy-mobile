"""Strict, evidence-bearing intent assessment; no generated Python is accepted here."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt

Number = Annotated[StrictInt | StrictFloat, Field(allow_inf_nan=False)]
Decision = Literal["accepted", "needs_clarification", "rejected"]
Reason = Literal[
    "ok", "non_strategy", "instruction_override", "profit_guarantee",
    "incomplete", "unsupported", "contradictory", "invalid_parameters",
]
Missing = Literal[
    "entry_rule", "exit_rule", "threshold", "comparison",
    "indicator_reference", "parameter", "trailing_percent",
]
Parameter = Literal["window", "window_fast", "window_slow", "window_signal", "deviation", "smooth_window"]


class StrictAssessmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class IntentIndicator(StrictAssessmentModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    family: Literal["rsi", "sma", "ema", "macd", "bollinger", "stochastic", "atr"]
    role: Literal["single", "fast", "slow"]
    evidence: str = Field(min_length=1, max_length=2000)
    parameters: dict[Parameter, Number]
    parameter_evidence: dict[Parameter, str]


class IntentOperand(StrictAssessmentModel):
    kind: Literal["indicator", "price", "constant", "add", "subtract", "multiply", "divide"]
    reference: Annotated[str, Field(pattern=r"^(?:[a-z][a-z0-9_]{0,31}\.(?:value|line|signal|histogram|lower|middle|upper|k|d)|open|high|low|close|volume)$")] | None
    value: Number | None
    evidence: str = Field(min_length=1, max_length=2000)
    arguments: list["IntentOperand"] = Field(default_factory=list, max_length=2)


class IntentCondition(StrictAssessmentModel):
    operator: Literal[
        "lt", "lte", "gt", "gte", "eq", "cross_above", "cross_below", "and", "or", "not",
    ]
    left: IntentOperand | None
    right: IntentOperand | None
    children: list["IntentCondition"] = Field(max_length=8)


class IntentRule(StrictAssessmentModel):
    action: Literal["buy", "close"]
    evidence: str = Field(min_length=1, max_length=2000)
    condition: IntentCondition


class IntentTrailingStop(StrictAssessmentModel):
    percent: Number
    evidence: str = Field(min_length=1, max_length=2000)


class IntentAssessment(StrictAssessmentModel):
    decision: Decision
    reason_code: Reason
    entry: IntentRule | None
    exit: IntentRule | None
    indicators: list[IntentIndicator] = Field(max_length=8)
    missing_fields: list[Missing] = Field(max_length=7)
    unsupported_features: list[str] = Field(max_length=8)
    trailing_stop: IntentTrailingStop | None


class DefaultApplied(BaseModel):
    indicator_id: str
    family: str
    parameter: str
    value: Number


class AdmissionSummary(BaseModel):
    decision: Literal["accepted"] = "accepted"
    defaults_applied: list[DefaultApplied] = Field(default_factory=list)


class AdmissionFailure(BaseModel):
    detail: str
    decision: Literal["needs_clarification", "rejected"]
    reason_code: str
    questions: list[str] = Field(default_factory=list)
