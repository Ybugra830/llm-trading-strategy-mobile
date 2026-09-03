"""Repository-owned deterministic fixtures, never executed on the host."""
from app.llm.prompt_examples import CANONICAL_STRATEGY_EXAMPLES

TRAILING_SOURCE = CANONICAL_STRATEGY_EXAMPLES[0].source.strip()
RSI_SOURCE = TRAILING_SOURCE[:TRAILING_SOURCE.index("        for trade")] + TRAILING_SOURCE[TRAILING_SOURCE.index("        if not self.position"):]
EMA_RSI_SOURCE = '''from backtesting import Strategy
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator

def rsi_array(values, window):
    return RSIIndicator(pd.Series(values), window=window).rsi().to_numpy()

def ema_array(values, window):
    return EMAIndicator(pd.Series(values), window=window).ema_indicator().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        self.fast = self.I(ema_array, self.data.Close, 20)
        self.slow = self.I(ema_array, self.data.Close, 50)
        self.rsi = self.I(rsi_array, self.data.Close, 14)

    def next(self):
        cross_down = self.fast[-2] >= self.slow[-2] and self.fast[-1] < self.slow[-1]
        if not self.position and self.fast[-1] > self.slow[-1] and self.rsi[-1] < 40:
            self.buy()
        elif self.position and (cross_down or self.rsi[-1] > 70):
            self.position.close()
'''
SOURCES = (RSI_SOURCE, TRAILING_SOURCE, EMA_RSI_SOURCE)
