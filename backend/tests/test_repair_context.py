"""Deterministic indicator classification and safe repair context tests."""

from app.llm.repair_context import (
    build_repair_context,
    detect_indicator_families,
    static_failure_type,
)
from app.schemas.validation import StrategyValidationResponse
from app.runtime.models import SafeFailureContext


def test_detects_families_from_source_before_prompt_fallback() -> None:
    code = "from ta.trend import SMAIndicator\nfrom ta.momentum import RSIIndicator"
    assert detect_indicator_families(code, "unrelated request") == ("RSI", "SMA")


def test_turkish_prompt_fallback_detects_sma() -> None:
    assert detect_indicator_families("not valid python", "20 günlük SMA yukarı kesti") == (
        "SMA",
    )


def test_sma_runtime_context_contains_exact_api_guidance_and_is_bounded() -> None:
    context = build_repair_context(
        stage="smoke",
        failure_type=" AttributeError ",
        code="from ta.trend import SMAIndicator",
        prompt="SMA crossover",
        safe_findings=[" runtime   failed "],
        runtime_context=SafeFailureContext(family="indicator_adapter", finding="invalid_indicator_attribute", api="indicator.unsupported_attribute"),
    )

    assert context.failure_type == "AttributeError"
    assert context.indicator_families == ("SMA",)
    assert context.safe_findings == ("runtime failed",)
    assert any("sma_indicator()" in item for item in context.compatibility_guidance)
    assert all("traceback" not in item.casefold() for item in context.compatibility_guidance)


def test_syntax_failure_is_not_misreported_as_every_validation_category() -> None:
    validation = StrategyValidationResponse(
        valid=False,
        syntax_valid=False,
        imports_valid=False,
        security_valid=False,
        interface_valid=False,
        lookahead_valid=False,
        errors=["Sözdizimi hatası: invalid syntax"],
    )

    assert static_failure_type(validation) == "SyntaxValidationError"
