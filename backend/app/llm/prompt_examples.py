"""Canonical bilingual strategy examples used by the LLM contract."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CanonicalStrategyExample:
    family: str
    english: str
    turkish: str
    source: str

    def as_prompt_text(self) -> str:
        return (
            f"### {self.family}\n"
            f"EN: {self.english}\n"
            f"TR: {self.turkish}\n"
            f"Canonical implementation:\n{self.source.strip()}"
        )


CANONICAL_STRATEGY_EXAMPLES = (
    CanonicalStrategyExample(
        family="RSI + trailing stop",
        english="Buy when RSI(14) is below 30. Close the long position when RSI(14) exceeds 70. Apply a 3 percent trailing stop loss to the open long position.",
        turkish="RSI(14) 30'un altındayken al. RSI(14) 70'i aştığında uzun pozisyonu kapat. Açık uzun pozisyona %3 iz süren zarar durdur uygula.",
        source="""
from backtesting import Strategy
import pandas as pd
from ta.momentum import RSIIndicator

def rsi_array(values, window):
    return RSIIndicator(pd.Series(values), window=window).rsi().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        self.rsi = self.I(rsi_array, self.data.Close, 14)

    def next(self):
        for trade in self.trades:
            trade.sl = max(
                trade.sl or trade.entry_price * (1 - 0.03),
                self.data.High[-1] * (1 - 0.03),
            )
        if not self.position and self.rsi[-1] < 30:
            self.buy()
        elif self.position and self.rsi[-1] > 70:
            self.position.close()
""",
    ),
    CanonicalStrategyExample(
        family="RSI",
        english="Buy when RSI is below 35 and close when RSI is above 70.",
        turkish="RSI 35'in altına düştüğünde al, RSI 70'in üzerine çıktığında pozisyonu kapat.",
        source="""
from backtesting import Strategy
import pandas as pd
from ta.momentum import RSIIndicator

def rsi_array(values, window):
    series = pd.Series(values)
    return RSIIndicator(series, window=window).rsi().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        self.rsi = self.I(rsi_array, self.data.Close, 14)

    def next(self):
        if not self.position and self.rsi[-1] < 35:
            self.buy()
        elif self.position and self.rsi[-1] > 70:
            self.position.close()
""",
    ),
    CanonicalStrategyExample(
        family="SMA",
        english="Buy when SMA20 crosses above SMA50 and close when SMA20 crosses below SMA50.",
        turkish="20 günlük SMA 50 günlük SMA'yı yukarı kestiğinde al, aşağı kestiğinde pozisyonu kapat.",
        source="""
from backtesting import Strategy
import pandas as pd
from ta.trend import SMAIndicator

def sma_array(values, window):
    series = pd.Series(values)
    return SMAIndicator(series, window=window).sma_indicator().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        self.fast = self.I(sma_array, self.data.Close, 20)
        self.slow = self.I(sma_array, self.data.Close, 50)

    def next(self):
        cross_up = self.fast[-2] <= self.slow[-2] and self.fast[-1] > self.slow[-1]
        cross_down = self.fast[-2] >= self.slow[-2] and self.fast[-1] < self.slow[-1]
        if not self.position and cross_up:
            self.buy()
        elif self.position and cross_down:
            self.position.close()
""",
    ),
    CanonicalStrategyExample(
        family="EMA",
        english="Buy when EMA10 crosses above EMA30 and close when EMA10 crosses below EMA30.",
        turkish="10 günlük EMA 30 günlük EMA'yı yukarı kestiğinde al, aşağı kestiğinde pozisyonu kapat.",
        source="""
from backtesting import Strategy
import pandas as pd
from ta.trend import EMAIndicator

def ema_array(values, window):
    series = pd.Series(values)
    return EMAIndicator(series, window=window).ema_indicator().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        self.fast = self.I(ema_array, self.data.Close, 10)
        self.slow = self.I(ema_array, self.data.Close, 30)

    def next(self):
        cross_up = self.fast[-2] <= self.slow[-2] and self.fast[-1] > self.slow[-1]
        cross_down = self.fast[-2] >= self.slow[-2] and self.fast[-1] < self.slow[-1]
        if not self.position and cross_up:
            self.buy()
        elif self.position and cross_down:
            self.position.close()
""",
    ),
    CanonicalStrategyExample(
        family="MACD",
        english="Buy when MACD crosses above its signal line and close when it crosses below.",
        turkish="MACD sinyal çizgisini yukarı kestiğinde al, aşağı kestiğinde pozisyonu kapat.",
        source="""
from backtesting import Strategy
import pandas as pd
from ta.trend import MACD

def macd_line_array(values):
    series = pd.Series(values)
    return MACD(series, window_slow=26, window_fast=12, window_sign=9).macd().to_numpy()

def macd_signal_array(values):
    series = pd.Series(values)
    return MACD(series, window_slow=26, window_fast=12, window_sign=9).macd_signal().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        self.macd = self.I(macd_line_array, self.data.Close)
        self.signal = self.I(macd_signal_array, self.data.Close)

    def next(self):
        cross_up = self.macd[-2] <= self.signal[-2] and self.macd[-1] > self.signal[-1]
        cross_down = self.macd[-2] >= self.signal[-2] and self.macd[-1] < self.signal[-1]
        if not self.position and cross_up:
            self.buy()
        elif self.position and cross_down:
            self.position.close()
""",
    ),
    CanonicalStrategyExample(
        family="Bollinger Bands",
        english="Buy when price closes below the lower Bollinger Band and RSI is below 35; close when price reaches the middle band.",
        turkish="Fiyat alt Bollinger Bandının altında kapanır ve RSI 35'in altındaysa al; fiyat orta banda ulaştığında pozisyonu kapat.",
        source="""
from backtesting import Strategy
import pandas as pd
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

def lower_band_array(values):
    series = pd.Series(values)
    return BollingerBands(series, window=20, window_dev=2).bollinger_lband().to_numpy()

def middle_band_array(values):
    series = pd.Series(values)
    return BollingerBands(series, window=20, window_dev=2).bollinger_mavg().to_numpy()

def rsi_array(values):
    series = pd.Series(values)
    return RSIIndicator(series, window=14).rsi().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        self.lower = self.I(lower_band_array, self.data.Close)
        self.middle = self.I(middle_band_array, self.data.Close)
        self.rsi = self.I(rsi_array, self.data.Close)

    def next(self):
        close = self.data.Close[-1]
        if not self.position and close < self.lower[-1] and self.rsi[-1] < 35:
            self.buy()
        elif self.position and close >= self.middle[-1]:
            self.position.close()
""",
    ),
    CanonicalStrategyExample(
        family="Stochastic",
        english="Buy when stochastic K crosses above D below 20; close when K crosses below D above 80.",
        turkish="Stokastik K, 20'nin altında D'yi yukarı kestiğinde al; 80'in üstünde aşağı kestiğinde pozisyonu kapat.",
        source="""
from backtesting import Strategy
import pandas as pd
from ta.momentum import StochasticOscillator

def stochastic_k_array(high, low, close):
    indicator = StochasticOscillator(pd.Series(high), pd.Series(low), pd.Series(close), window=14, smooth_window=3)
    return indicator.stoch().to_numpy()

def stochastic_d_array(high, low, close):
    indicator = StochasticOscillator(pd.Series(high), pd.Series(low), pd.Series(close), window=14, smooth_window=3)
    return indicator.stoch_signal().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        inputs = (self.data.High, self.data.Low, self.data.Close)
        self.k = self.I(stochastic_k_array, *inputs)
        self.d = self.I(stochastic_d_array, *inputs)

    def next(self):
        cross_up = self.k[-2] <= self.d[-2] and self.k[-1] > self.d[-1]
        cross_down = self.k[-2] >= self.d[-2] and self.k[-1] < self.d[-1]
        if not self.position and cross_up and self.k[-1] < 20:
            self.buy()
        elif self.position and cross_down and self.k[-1] > 80:
            self.position.close()
""",
    ),
    CanonicalStrategyExample(
        family="ATR",
        english="Buy when price crosses above SMA20 plus ATR14; close when price crosses below SMA20.",
        turkish="Fiyat SMA20 artı ATR14 seviyesini yukarı kestiğinde al; SMA20'yi aşağı kestiğinde pozisyonu kapat.",
        source="""
from backtesting import Strategy
import pandas as pd
from ta.trend import SMAIndicator
from ta.volatility import AverageTrueRange

def sma_array(values):
    return SMAIndicator(pd.Series(values), window=20).sma_indicator().to_numpy()

def atr_array(high, low, close):
    indicator = AverageTrueRange(pd.Series(high), pd.Series(low), pd.Series(close), window=14)
    return indicator.average_true_range().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        self.sma = self.I(sma_array, self.data.Close)
        self.atr = self.I(atr_array, self.data.High, self.data.Low, self.data.Close)

    def next(self):
        previous_entry = self.sma[-2] + self.atr[-2]
        current_entry = self.sma[-1] + self.atr[-1]
        cross_up = self.data.Close[-2] <= previous_entry and self.data.Close[-1] > current_entry
        cross_down = self.data.Close[-2] >= self.sma[-2] and self.data.Close[-1] < self.sma[-1]
        if not self.position and cross_up:
            self.buy()
        elif self.position and cross_down:
            self.position.close()
""",
    ),
)


def canonical_examples_prompt() -> str:
    return "\n\n".join(example.as_prompt_text() for example in CANONICAL_STRATEGY_EXAMPLES)
