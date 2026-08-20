"""Backtesting.py Series değerlerinin JSON-safe metrik dönüşüm testleri."""

import json
import math

import numpy as np
import pandas as pd
import pytest

from app.backtest.errors import BacktestExecutionError
from app.backtest.metrics import extract_backtest_metrics


def test_metrics_are_json_safe_and_net_profit_is_calculated(
    backtest_stats: pd.Series,
) -> None:
    stats = backtest_stats.copy()
    stats["Sharpe Ratio"] = np.nan
    stats["Sortino Ratio"] = np.inf
    stats["Win Rate [%]"] = -np.inf

    metrics = extract_backtest_metrics(stats, initial_cash=100_000)
    payload = metrics.model_dump()

    assert metrics.final_equity == 108_500
    assert metrics.net_profit == 8_500
    assert metrics.number_of_trades == 4
    assert metrics.average_trade_duration == "8 days 00:00:00"
    assert metrics.sharpe_ratio is None
    assert metrics.sortino_ratio is None
    assert metrics.win_rate_percent is None
    json.dumps(payload, allow_nan=False)
    assert not any(
        isinstance(value, float) and not math.isfinite(value)
        for value in payload.values()
    )


def test_zero_trade_metrics_keep_unavailable_values_null(
    backtest_stats: pd.Series,
) -> None:
    stats = backtest_stats.copy()
    stats["# Trades"] = np.int64(0)
    for key in (
        "Win Rate [%]",
        "Sharpe Ratio",
        "Sortino Ratio",
        "Profit Factor",
        "Best Trade [%]",
        "Worst Trade [%]",
    ):
        stats[key] = np.nan
    stats["Avg. Trade Duration"] = pd.NaT

    metrics = extract_backtest_metrics(stats, initial_cash=100_000)

    assert metrics.number_of_trades == 0
    assert metrics.win_rate_percent is None
    assert metrics.sharpe_ratio is None
    assert metrics.average_trade_duration is None


def test_missing_official_stat_key_is_an_engine_error(
    backtest_stats: pd.Series,
) -> None:
    with pytest.raises(BacktestExecutionError):
        extract_backtest_metrics(backtest_stats.drop("Equity Final [$]"), 100_000)
