"""Supported-indicator, prompt ve print politikası testleri."""

from app.indicators.registry import SUPPORTED_INDICATORS
from app.llm.prompt_builder import STRATEGY_SYSTEM_PROMPT, build_repair_messages
from app.llm.prompt_examples import CANONICAL_STRATEGY_EXAMPLES
from app.llm.repair_context import RepairFailureContext
from app.services.validation_service import ValidationService


def test_supported_indicator_registry_is_ordered_and_uses_approved_ta_modules() -> None:
    assert [item.display_name for item in SUPPORTED_INDICATORS] == [
        "SMA",
        "EMA",
        "RSI",
        "MACD",
        "Bollinger Bands",
        "Stochastic",
        "ATR",
    ]
    assert {item.approved_module for item in SUPPORTED_INDICATORS} == {
        "ta.trend",
        "ta.momentum",
        "ta.volatility",
    }
    assert all(item.supported for item in SUPPORTED_INDICATORS)


def test_generation_prompt_contains_supported_indicator_contract() -> None:
    for indicator in SUPPORTED_INDICATORS:
        assert indicator.display_name in STRATEGY_SYSTEM_PROMPT
        assert indicator.approved_module in STRATEGY_SYSTEM_PROMPT


def test_generation_prompt_requires_backtesting_ta_adapter() -> None:
    assert "Never override Strategy.__init__" in STRATEGY_SYSTEM_PROMPT
    assert "self.I" in STRATEGY_SYSTEM_PROMPT
    assert "pandas.Series" in STRATEGY_SYSTEM_PROMPT
    assert "to_numpy" in STRATEGY_SYSTEM_PROMPT
    assert "self.position.close()" in STRATEGY_SYSTEM_PROMPT
    assert "SMAIndicator(...).sma_indicator()" in STRATEGY_SYSTEM_PROMPT
    assert "there is no SMAIndicator.sma()" in STRATEGY_SYSTEM_PROMPT
    assert "previous bar [-2] and current bar [-1]" in STRATEGY_SYSTEM_PROMPT


def test_canonical_examples_are_bilingual_and_statically_valid() -> None:
    assert [example.family for example in CANONICAL_STRATEGY_EXAMPLES] == [
        "RSI + trailing stop",
        "RSI",
        "SMA",
        "EMA",
        "MACD",
        "Bollinger Bands",
        "Stochastic",
        "ATR",
    ]
    validator = ValidationService()
    for example in CANONICAL_STRATEGY_EXAMPLES:
        assert example.english in STRATEGY_SYSTEM_PROMPT
        assert example.turkish in STRATEGY_SYSTEM_PROMPT
        assert validator.validate(example.source, example.english).valid, example.family
        assert validator.validate(example.source, example.turkish).valid, example.family


def test_repair_prompt_preserves_original_code_and_safe_errors() -> None:
    messages = build_repair_messages(
        "RSI düşükken al.",
        "class GeneratedStrategy: pass",
        RepairFailureContext(
            stage="static",
            failure_type="InterfaceValidationError",
            indicator_families=("RSI",),
            safe_findings=("GeneratedStrategy sınıfı bulunamadı.",),
            compatibility_guidance=("Use self.I.",),
        ),
    )

    user_message = messages[1]["content"]
    assert "RSI düşükken al." in user_message
    assert "class GeneratedStrategy: pass" in user_message
    assert "GeneratedStrategy sınıfı bulunamadı." in user_message
    assert "Failure stage: static" in user_message
    assert "Failure type: InterfaceValidationError" in user_message
    assert "Indicator families: RSI" in user_message


def test_generated_print_call_is_rejected() -> None:
    result = ValidationService().validate(
        """\
from backtesting import Strategy

class GeneratedStrategy(Strategy):
    def init(self):
        pass

    def next(self):
        print("spam")
"""
    )

    assert result.valid is False
    assert "Yasaklı fonksiyon çağrısı: print" in result.errors
