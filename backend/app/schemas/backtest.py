"""BIST backtest endpoint'inin request ve response şemaları."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.market.bist_symbols import normalize_bist_symbol


class BistBacktestRequest(BaseModel):
    """Güvenilir Day 4 BIST backtest isteği."""

    symbol: str = Field(min_length=1, max_length=16)
    initial_cash: float = Field(default=100_000, gt=0, allow_inf_nan=False)
    commission: float = Field(default=0.002, ge=0, lt=0.1, allow_inf_nan=False)

    @field_validator("symbol", mode="before")
    @classmethod
    def normalize_symbol(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_bist_symbol(value)
        return value


class BacktestDataSummary(BaseModel):
    """Temiz veri ve kronolojik split görünümü."""

    download_start: date
    download_end: date
    total_rows: int = Field(ge=0)
    history_rows: int = Field(ge=0)
    test_rows: int = Field(ge=0)
    cutoff_date: date
    test_start: date
    test_end: date


class BacktestConfiguration(BaseModel):
    """Çalıştırılan backtest ayarları."""

    initial_cash: float
    commission: float
    strategy: Literal["reference_sma_cross"]


class BacktestMetrics(BaseModel):
    """JSON-safe backtesting.py performans metrikleri."""

    initial_cash: float
    final_equity: float | None
    net_profit: float | None
    return_percent: float | None
    buy_and_hold_return_percent: float | None
    number_of_trades: int
    win_rate_percent: float | None
    max_drawdown_percent: float | None
    sharpe_ratio: float | None
    sortino_ratio: float | None
    profit_factor: float | None
    best_trade_percent: float | None
    worst_trade_percent: float | None
    average_trade_duration: str | None
    exposure_time_percent: float | None


class BistBacktestResponse(BaseModel):
    """BIST piyasa verisi ve trusted strategy backtest sonucu."""

    symbol: str
    yahoo_symbol: str
    data: BacktestDataSummary
    configuration: BacktestConfiguration
    metrics: BacktestMetrics
