"""backtesting.py sonuçlarını JSON-safe response metriklerine dönüştürür."""

import math
from collections.abc import Mapping
from typing import Any

import pandas as pd

from app.backtest.errors import BacktestExecutionError
from app.schemas.backtest import BacktestMetrics


def _required(stats: Mapping[str, Any], key: str) -> Any:
    try:
        return stats[key]
    except KeyError as exc:
        raise BacktestExecutionError from exc


def _optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        converted = float(value)
    except (TypeError, ValueError) as exc:
        raise BacktestExecutionError from exc
    return converted if math.isfinite(converted) else None


def _trade_count(value: Any) -> int:
    converted = _optional_float(value)
    if converted is None or converted < 0:
        raise BacktestExecutionError
    return int(converted)


def _duration_string(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    try:
        duration = pd.Timedelta(value)
    except (TypeError, ValueError) as exc:
        raise BacktestExecutionError from exc
    return None if pd.isna(duration) else str(duration)


def extract_backtest_metrics(
    stats: Mapping[str, Any],
    initial_cash: float,
) -> BacktestMetrics:
    """Resmî stats anahtarlarını güvenli response değerlerine eşleştir."""
    final_equity = _optional_float(_required(stats, "Equity Final [$]"))
    net_profit = None if final_equity is None else final_equity - float(initial_cash)

    return BacktestMetrics(
        initial_cash=float(initial_cash),
        final_equity=final_equity,
        net_profit=net_profit,
        return_percent=_optional_float(_required(stats, "Return [%]")),
        buy_and_hold_return_percent=_optional_float(
            _required(stats, "Buy & Hold Return [%]")
        ),
        number_of_trades=_trade_count(_required(stats, "# Trades")),
        win_rate_percent=_optional_float(_required(stats, "Win Rate [%]")),
        max_drawdown_percent=_optional_float(
            _required(stats, "Max. Drawdown [%]")
        ),
        sharpe_ratio=_optional_float(_required(stats, "Sharpe Ratio")),
        sortino_ratio=_optional_float(_required(stats, "Sortino Ratio")),
        profit_factor=_optional_float(_required(stats, "Profit Factor")),
        best_trade_percent=_optional_float(_required(stats, "Best Trade [%]")),
        worst_trade_percent=_optional_float(_required(stats, "Worst Trade [%]")),
        average_trade_duration=_duration_string(
            _required(stats, "Avg. Trade Duration")
        ),
        exposure_time_percent=_optional_float(_required(stats, "Exposure Time [%]")),
    )
