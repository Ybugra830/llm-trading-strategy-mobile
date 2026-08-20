"""BIST verisinden trusted reference strategy backtest sonucu üretir."""

from collections.abc import Callable
from typing import Protocol

import pandas as pd
from backtesting import Strategy

from app.backtest.engine import run_backtest
from app.backtest.metrics import extract_backtest_metrics
from app.backtest.reference_strategies import ReferenceSmaCrossStrategy
from app.market.bist_symbols import normalize_bist_symbol, to_yahoo_symbol
from app.market.data_split import split_market_data
from app.market.ohlcv_cleaner import clean_ohlcv
from app.schemas.backtest import (
    BacktestConfiguration,
    BacktestDataSummary,
    BistBacktestRequest,
    BistBacktestResponse,
)


class MarketDataProvider(Protocol):
    """Backtest servisinin ihtiyaç duyduğu piyasa verisi arayüzü."""

    def download_daily(self, yahoo_symbol: str) -> pd.DataFrame: ...


BacktestRunner = Callable[[pd.DataFrame, type[Strategy], float, float], pd.Series]


class BacktestService:
    """Day 4 piyasa verisi ve güvenilir backtest akışını yönetir."""

    def __init__(
        self,
        provider: MarketDataProvider,
        runner: BacktestRunner = run_backtest,
        strategy_class: type[Strategy] = ReferenceSmaCrossStrategy,
    ) -> None:
        self._provider = provider
        self._runner = runner
        self._strategy_class = strategy_class

    def run_bist_backtest(self, request: BistBacktestRequest) -> BistBacktestResponse:
        """Yalnızca altı aylık test verisinde trusted strategy çalıştır."""
        symbol = normalize_bist_symbol(request.symbol)
        yahoo_symbol = to_yahoo_symbol(symbol)
        raw_data = self._provider.download_daily(yahoo_symbol)
        clean_data = clean_ohlcv(raw_data)
        split = split_market_data(clean_data)
        stats = self._runner(
            split.test_data,
            self._strategy_class,
            request.initial_cash,
            request.commission,
        )
        metrics = extract_backtest_metrics(stats, request.initial_cash)

        return BistBacktestResponse(
            symbol=symbol,
            yahoo_symbol=yahoo_symbol,
            data=BacktestDataSummary(
                download_start=clean_data.index.min().date(),
                download_end=clean_data.index.max().date(),
                total_rows=len(clean_data),
                history_rows=len(split.history_data),
                test_rows=len(split.test_data),
                cutoff_date=split.cutoff_date.date(),
                test_start=split.test_data.index.min().date(),
                test_end=split.test_data.index.max().date(),
            ),
            configuration=BacktestConfiguration(
                initial_cash=request.initial_cash,
                commission=request.commission,
                strategy="reference_sma_cross",
            ),
            metrics=metrics,
        )
