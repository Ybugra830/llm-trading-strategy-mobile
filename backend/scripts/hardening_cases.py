"""The exact acceptance prompts and fixed benchmark configuration."""
from dataclasses import dataclass

PRODUCTION_MODEL = "nvidia/nemotron-3-super-120b-a12b"
COMPARISON_MODEL = "mistralai/mistral-nemotron"


@dataclass(frozen=True)
class Case:
    name: str
    prompt: str
    cash: int


CASES = (
    Case("rsi", "Buy when RSI(14) drops below 30. Close the long position when RSI(14) exceeds 70.", 10000),
    Case("rsi_trailing", "Buy when RSI(14) drops below 30. Close the long position when RSI(14) exceeds 70. Apply a 3 percent trailing stop loss to the open long position.", 10000),
    Case("ema_rsi", "Buy when the 20-period EMA is greater than the 50-period EMA and RSI(14) is below 40. Close the position when the 20-period EMA crosses below the 50-period EMA or RSI is above 70.", 100000),
)
