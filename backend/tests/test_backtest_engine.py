"""Trusted strategy ve backtesting.py engine yapılandırma testleri."""

import pandas as pd
import pytest
from backtesting import Strategy

from app.backtest.engine import run_backtest
from app.backtest.errors import BacktestExecutionError
from app.backtest.metrics import extract_backtest_metrics
from app.backtest.reference_strategies import ReferenceSmaCrossStrategy


def test_engine_passes_required_backtesting_configuration(
    monkeypatch: pytest.MonkeyPatch,
    ohlcv_data: pd.DataFrame,
    backtest_stats: pd.Series,
) -> None:
    captured: dict[str, object] = {}

    class FakeBacktest:
        def __init__(self, data: pd.DataFrame, strategy: type[Strategy], **kwargs: object):
            captured["data"] = data
            captured["strategy"] = strategy
            captured.update(kwargs)

        def run(self) -> pd.Series:
            return backtest_stats

    monkeypatch.setattr("app.backtest.engine.Backtest", FakeBacktest)

    stats = run_backtest(
        ohlcv_data.tail(100),
        ReferenceSmaCrossStrategy,
        initial_cash=125_000,
        commission=0.003,
    )

    assert stats is backtest_stats
    assert captured["cash"] == 125_000
    assert captured["commission"] == 0.003
    assert captured["exclusive_orders"] is True
    assert captured["trade_on_close"] is False
    assert captured["finalize_trades"] is True


def test_engine_wraps_unexpected_library_failure(
    monkeypatch: pytest.MonkeyPatch,
    ohlcv_data: pd.DataFrame,
) -> None:
    class FailingBacktest:
        def __init__(self, *_: object, **__: object) -> None:
            raise RuntimeError("library internals")

    monkeypatch.setattr("app.backtest.engine.Backtest", FailingBacktest)

    with pytest.raises(BacktestExecutionError):
        run_backtest(ohlcv_data.tail(100), ReferenceSmaCrossStrategy)


def test_reference_strategy_completes_on_deterministic_data(
    ohlcv_data: pd.DataFrame,
) -> None:
    stats = run_backtest(ohlcv_data.tail(130), ReferenceSmaCrossStrategy)

    assert isinstance(stats, pd.Series)
    assert "Equity Final [$]" in stats
    assert int(stats["# Trades"]) >= 0


def test_no_trade_strategy_is_a_successful_backtest(
    ohlcv_data: pd.DataFrame,
) -> None:
    class NoTradeStrategy(Strategy):
        def init(self) -> None:
            pass

        def next(self) -> None:
            pass

    stats = run_backtest(ohlcv_data.tail(130), NoTradeStrategy)
    metrics = extract_backtest_metrics(stats, 100_000)

    assert metrics.number_of_trades == 0
    assert metrics.win_rate_percent is None
