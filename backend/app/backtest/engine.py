"""backtesting.py motorunu güvenilir Strategy sınıflarıyla çalıştırır."""

import logging

import pandas as pd
from backtesting import Backtest, Strategy

from app.backtest.errors import BacktestExecutionError

logger = logging.getLogger(__name__)


def run_backtest(
    data: pd.DataFrame,
    strategy_class: type[Strategy],
    initial_cash: float = 100_000,
    commission: float = 0.002,
) -> pd.Series:
    """Tarihsel test penceresini çalıştırıp backtesting.py stats döndür."""
    try:
        # Per-run subclass: never mutate a shared repository strategy class.
        # Match the sandbox's terminal-entry policy without changing exits.
        class EndBoundedStrategy(strategy_class):
            def next(self):
                super().next()
                if len(self.data) == len(data):
                    for order in tuple(self.orders):
                        if order.parent_trade is None:
                            order.cancel()

        EndBoundedStrategy.__name__ = strategy_class.__name__
        backtest = Backtest(
            data,
            EndBoundedStrategy,
            cash=initial_cash,
            commission=commission,
            exclusive_orders=True,
            trade_on_close=False,
            finalize_trades=True,
        )
        return backtest.run()
    except Exception as exc:
        logger.error("Backtest execution failed error_type=%s", type(exc).__name__)
        raise BacktestExecutionError from exc
