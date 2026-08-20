"""BIST backtest HTTP sözleşmesi ve güvenli hata eşleme testleri."""

import asyncio
from datetime import date

import httpx
import pytest

from app.api.backtest_routes import get_backtest_service
from app.backtest.errors import BacktestExecutionError
from app.main import app
from app.market.errors import (
    InsufficientMarketDataError,
    InvalidMarketDataError,
    MarketDataUnavailableError,
    UnsupportedBistSymbolError,
)
from app.schemas.backtest import (
    BacktestConfiguration,
    BacktestDataSummary,
    BacktestMetrics,
    BistBacktestRequest,
    BistBacktestResponse,
)


def _response(symbol: str) -> BistBacktestResponse:
    return BistBacktestResponse(
        symbol=symbol,
        yahoo_symbol=f"{symbol}.IS",
        data=BacktestDataSummary(
            download_start=date(2023, 7, 3),
            download_end=date(2026, 6, 30),
            total_rows=780,
            history_rows=650,
            test_rows=130,
            cutoff_date=date(2025, 12, 30),
            test_start=date(2025, 12, 30),
            test_end=date(2026, 6, 30),
        ),
        configuration=BacktestConfiguration(
            initial_cash=100_000,
            commission=0.002,
            strategy="reference_sma_cross",
        ),
        metrics=BacktestMetrics(
            initial_cash=100_000,
            final_equity=105_000,
            net_profit=5_000,
            return_percent=5,
            buy_and_hold_return_percent=4,
            number_of_trades=2,
            win_rate_percent=50,
            max_drawdown_percent=-2,
            sharpe_ratio=1,
            sortino_ratio=1.2,
            profit_factor=1.5,
            best_trade_percent=3,
            worst_trade_percent=-1,
            average_trade_duration="5 days 00:00:00",
            exposure_time_percent=25,
        ),
    )


class SuccessfulBacktestService:
    def run_bist_backtest(self, request: BistBacktestRequest) -> BistBacktestResponse:
        return _response(request.symbol)


def post_bist(payload: dict[str, object]) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post("/api/v1/backtests/bist", json=payload)

    return asyncio.run(send_request())


def test_valid_backtest_request_returns_http_200() -> None:
    app.dependency_overrides[get_backtest_service] = SuccessfulBacktestService
    try:
        response = post_bist(
            {"symbol": " thyao ", "initial_cash": 100_000, "commission": 0.002}
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["symbol"] == "THYAO"
    assert response.json()["metrics"]["net_profit"] == 5_000


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (
            UnsupportedBistSymbolError(),
            422,
            "Desteklenmeyen BIST sembolü.",
        ),
        (
            InsufficientMarketDataError(),
            422,
            "Backtest için yeterli piyasa verisi bulunamadı.",
        ),
        (
            MarketDataUnavailableError("Yahoo internal details"),
            502,
            "Piyasa verisi şu anda kullanılamıyor.",
        ),
        (
            InvalidMarketDataError("DataFrame internal details"),
            502,
            "Piyasa verisi şu anda kullanılamıyor.",
        ),
        (
            BacktestExecutionError("engine internal details"),
            500,
            "Backtest şu anda çalıştırılamıyor.",
        ),
    ],
)
def test_expected_failures_use_safe_http_messages(
    error: Exception,
    expected_status: int,
    expected_detail: str,
) -> None:
    class FailingService:
        def run_bist_backtest(self, request: BistBacktestRequest) -> BistBacktestResponse:
            raise error

    app.dependency_overrides[get_backtest_service] = FailingService
    try:
        response = post_bist({"symbol": "THYAO"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert "internal details" not in response.text


@pytest.mark.parametrize(
    "payload",
    [
        {"symbol": ""},
        {"symbol": "THYAO", "initial_cash": 0},
        {"symbol": "THYAO", "initial_cash": "Infinity"},
        {"symbol": "THYAO", "commission": -0.1},
        {"symbol": "THYAO", "commission": 0.1},
    ],
)
def test_invalid_request_values_return_http_422(payload: dict[str, object]) -> None:
    app.dependency_overrides[get_backtest_service] = SuccessfulBacktestService
    try:
        response = post_bist(payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
