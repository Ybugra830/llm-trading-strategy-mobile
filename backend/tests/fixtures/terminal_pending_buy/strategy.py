from backtesting import Strategy
import pandas as pd
from ta.trend import SMAIndicator

def average(values, window):
    return SMAIndicator(pd.Series(values), window=window).sma_indicator().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        self.fast = self.I(average, self.data.Close, 3)
        self.slow = self.I(average, self.data.Close, 5)

    def next(self):
        if not self.position and len(self.data) - 1 in [19]:
            self.buy()
        elif self.position and len(self.data) - 1 in []:
            self.position.close()
