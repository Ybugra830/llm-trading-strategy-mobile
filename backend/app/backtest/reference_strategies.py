"""Day 4 backtest altyapısını doğrulayan güvenilir referans stratejiler."""

import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover


def _simple_moving_average(values: object, period: int) -> object:
    """Yalnızca geçmiş/mevcut değerlerden rolling SMA üret."""
    return pd.Series(values).rolling(period).mean().to_numpy()


class ReferenceSmaCrossStrategy(Strategy):
    """Backtest altyapısı için repository-owned, long-only SMA stratejisi."""

    fast_period = 10
    slow_period = 20

    def init(self) -> None:
        self.fast_sma = self.I(
            _simple_moving_average,
            self.data.Close,
            self.fast_period,
        )
        self.slow_sma = self.I(
            _simple_moving_average,
            self.data.Close,
            self.slow_period,
        )

    def next(self) -> None:
        if crossover(self.fast_sma, self.slow_sma) and not self.position:
            self.buy()
        elif crossover(self.slow_sma, self.fast_sma) and self.position:
            self.position.close()
