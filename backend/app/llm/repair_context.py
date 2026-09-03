"""Safe, deterministic context supplied to strategy repair requests."""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from typing import Literal

from app.schemas.validation import StrategyValidationResponse
from app.runtime.models import SafeFailureContext


RepairStage = Literal["static", "smoke"]
KNOWN_FAMILIES = (
    "RSI",
    "SMA",
    "EMA",
    "MACD",
    "Bollinger Bands",
    "Stochastic",
    "ATR",
)

_FAMILY_MARKERS = {
    "RSI": ("rsiindicator", "rsi"),
    "SMA": ("smaindicator", "sma", "simple moving", "hareketli ortalama"),
    "EMA": ("emaindicator", "ema", "exponential moving", "üssel hareketli"),
    "MACD": ("macd",),
    "Bollinger Bands": ("bollingerbands", "bollinger"),
    "Stochastic": ("stochasticoscillator", "stochastic", "stokastik"),
    "ATR": ("averagetruerange", "atr", "average true range"),
}

_COMMON_GUIDANCE = (
    "Register every indicator in init() with self.I(...).",
    "Convert backtesting data arrays to pandas.Series inside the self.I helper.",
    "Return a NumPy-compatible array of identical length from every helper.",
    "Calculate no ta indicator in next(); read registered arrays there.",
)

_FAMILY_GUIDANCE = {
    "RSI": ("Use RSIIndicator(...).rsi().to_numpy().",),
    "SMA": (
        "Use SMAIndicator(...).sma_indicator().to_numpy(); SMAIndicator has no sma() method.",
        "Read moving-average crossovers with explicit [-2] and [-1] comparisons.",
    ),
    "EMA": (
        "Use EMAIndicator(...).ema_indicator().to_numpy().",
        "Read moving-average crossovers with explicit [-2] and [-1] comparisons.",
    ),
    "MACD": (
        "Register MACD.macd() and MACD.macd_signal() as separate self.I arrays.",
        "Read MACD crossovers with explicit [-2] and [-1] comparisons.",
    ),
    "Bollinger Bands": (
        "Register bollinger_lband(), bollinger_mavg(), and bollinger_hband() outputs separately as needed.",
    ),
    "Stochastic": (
        "Pass pandas.Series versions of High, Low, and Close to StochasticOscillator.",
        "Register stoch() and stoch_signal() as separate self.I arrays.",
    ),
    "ATR": (
        "Pass pandas.Series versions of High, Low, and Close to AverageTrueRange and return average_true_range().to_numpy().",
    ),
}


@dataclass(frozen=True)
class RepairFailureContext:
    stage: RepairStage
    failure_type: str
    indicator_families: tuple[str, ...]
    safe_findings: tuple[str, ...]
    compatibility_guidance: tuple[str, ...]
    family: str = "indicator_adapter"


def detect_indicator_families(code: str, prompt: str) -> tuple[str, ...]:
    """Classify known indicator families without executing generated source."""
    searchable = f"{code}\n{prompt}".casefold()
    try:
        tree = ast.parse(code)
    except SyntaxError:
        tree = None
    if tree is not None:
        identifiers = [
            node.id.casefold()
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
        ]
        attributes = [
            node.attr.casefold()
            for node in ast.walk(tree)
            if isinstance(node, ast.Attribute)
        ]
        searchable = f"{searchable}\n{' '.join(identifiers + attributes)}"

    detected = []
    for family in KNOWN_FAMILIES:
        if any(
            re.search(rf"(?<![a-z0-9_]){re.escape(marker)}(?![a-z0-9_])", searchable)
            if marker.isalpha() and len(marker) <= 4
            else marker in searchable
            for marker in _FAMILY_MARKERS[family]
        ):
            detected.append(family)
    return tuple(detected) or ("Unknown",)


def static_failure_type(validation: StrategyValidationResponse) -> str:
    if not validation.syntax_valid:
        return "SyntaxValidationError"
    failures = []
    for valid, name in (
        (validation.imports_valid, "ImportValidationError"),
        (validation.security_valid, "SecurityValidationError"),
        (validation.interface_valid, "InterfaceValidationError"),
        (validation.lookahead_valid, "LookaheadValidationError"),
    ):
        if not valid:
            failures.append(name)
    return ", ".join(failures) or "StaticValidationError"


def build_repair_context(
    *,
    stage: RepairStage,
    failure_type: str,
    code: str,
    prompt: str,
    safe_findings: list[str],
    runtime_context: SafeFailureContext | None = None,
    contract_findings: tuple = (),
) -> RepairFailureContext:
    families = detect_indicator_families(code, prompt)
    position_failure = bool(contract_findings) or (
        runtime_context is not None and runtime_context.family == "position_management"
    )
    if position_failure:
        family = "position_management"
        guidance = [
            "Position.entry_price is not available; use Position truthiness and close() only.",
            "Trade.entry_price is available and Trade.sl is writable.",
            "Access active trades with for trade in self.trades; use supported trade/position APIs only.",
            "For a requested trailing stop, copy the canonical loop at the start of next(): trade.sl = max(trade.sl or trade.entry_price * (1 - p), self.data.High[-1] * (1 - p)). Replace p with the requested percentage divided by 100.",
        ]
        safe_findings = [item.message for item in contract_findings] if contract_findings else [
            "Invalid position attribute." if runtime_context.finding == "invalid_position_attribute"
            else "Invalid trade attribute."
        ]
    elif stage == "smoke" and runtime_context is None:
        family = "unknown"
        guidance = ["Use only documented backtesting.py 0.6.6 APIs; fix the reported failure without changing the user's intent."]
        safe_findings = ["Strategy failed during isolated smoke execution."]
    else:
        family = "indicator_adapter"
        guidance = list(_COMMON_GUIDANCE)
        for indicator in families:
            guidance.extend(_FAMILY_GUIDANCE.get(indicator, ()))
    return RepairFailureContext(
        stage=stage,
        failure_type=" ".join(failure_type.split())[:100],
        indicator_families=families,
        safe_findings=tuple(" ".join(item.split())[:300] for item in safe_findings[:10]),
        compatibility_guidance=tuple(dict.fromkeys(guidance)),
        family=family,
    )
