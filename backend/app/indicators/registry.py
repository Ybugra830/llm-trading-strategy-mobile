"""Strategy Lab için açık ve sınırlı indikatör registry'si."""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class IndicatorDefinition:
    """Onaylı bir indikatörün public ve üretim metadata'sı."""

    indicator_id: str
    display_name: str
    approved_module: str
    supported: bool = True


SUPPORTED_INDICATORS: Final[tuple[IndicatorDefinition, ...]] = (
    IndicatorDefinition("sma", "SMA", "ta.trend"),
    IndicatorDefinition("ema", "EMA", "ta.trend"),
    IndicatorDefinition("rsi", "RSI", "ta.momentum"),
    IndicatorDefinition("macd", "MACD", "ta.trend"),
    IndicatorDefinition("bollinger", "Bollinger Bands", "ta.volatility"),
    IndicatorDefinition("stochastic", "Stochastic", "ta.momentum"),
    IndicatorDefinition("atr", "ATR", "ta.volatility"),
)
