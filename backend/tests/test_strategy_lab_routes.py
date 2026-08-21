"""Strategy Lab public API ve güvenli hata eşleme testleri."""

import asyncio
from datetime import date

import httpx
import pytest

from app.api.strategy_lab_routes import get_strategy_lab_service
from app.llm.nvidia_client import NvidiaNimError
from app.main import app
from app.market.errors import MarketDataUnavailableError, UnsupportedBistSymbolError
from app.runtime.errors import (
    FrozenStrategyExecutionError,
    SandboxUnavailableError,
    StrategyPretestError,
)
from app.schemas.backtest import BacktestDataSummary, BacktestMetrics
from app.schemas.strategy_lab import (
    StrategyLabConfiguration,
    StrategyLabGeneration,
    StrategyLabRunResponse,
    StrategyLabRuntime,
)
from app.schemas.validation import StrategyValidationResponse


def successful_response() -> StrategyLabRunResponse:
    return StrategyLabRunResponse(
        generation=StrategyLabGeneration(
            model="test/model",
            attempt_count=2,
            repaired=True,
            code="safe generated code",
        ),
        validation=StrategyValidationResponse(
            valid=True,
            syntax_valid=True,
            imports_valid=True,
            security_valid=True,
            interface_valid=True,
            lookahead_valid=True,
            errors=[],
        ),
        runtime=StrategyLabRuntime(),
        symbol="THYAO",
        yahoo_symbol="THYAO.IS",
        data=BacktestDataSummary(
            download_start=date(2023, 1, 1),
            download_end=date(2026, 1, 1),
            total_rows=780,
            history_rows=650,
            test_rows=130,
            cutoff_date=date(2025, 7, 1),
            test_start=date(2025, 7, 1),
            test_end=date(2026, 1, 1),
        ),
        configuration=StrategyLabConfiguration(initial_cash=100_000, commission=0.002),
        metrics=BacktestMetrics(
            initial_cash=100_000,
            final_equity=101_000,
            net_profit=1_000,
            return_percent=1,
            buy_and_hold_return_percent=2,
            number_of_trades=1,
            win_rate_percent=100,
            max_drawdown_percent=-1,
            sharpe_ratio=1,
            sortino_ratio=1,
            profit_factor=2,
            best_trade_percent=1,
            worst_trade_percent=1,
            average_trade_duration="1 days 00:00:00",
            exposure_time_percent=10,
        ),
    )


def request(method: str, path: str, payload=None) -> httpx.Response:
    async def send() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, path, json=payload)

    return asyncio.run(send())


class SuccessfulService:
    async def run(self, request):
        return successful_response()


def test_capabilities_are_ordered_and_flutter_friendly() -> None:
    response = request("GET", "/api/v1/strategy-lab/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert data["supported_symbols"][:3] == ["THYAO", "ASELS", "TUPRS"]
    assert data["supported_indicators"] == [
        "SMA",
        "EMA",
        "RSI",
        "MACD",
        "Bollinger Bands",
        "Stochastic",
        "ATR",
    ]
    assert data["prompt"] == {"min_length": 5, "max_length": 2000}
    assert "sandbox" not in response.text.lower()


def test_strategy_lab_success_does_not_expose_internal_hash() -> None:
    app.dependency_overrides[get_strategy_lab_service] = SuccessfulService
    try:
        response = request(
            "POST",
            "/api/v1/strategy-lab/run",
            {"prompt": "RSI düşükken al ve yüksekken sat.", "symbol": " thyao "},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["generation"]["repaired"] is True
    assert "strategy_code_hash" not in response.text
    assert "container" not in response.text.lower()


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (UnsupportedBistSymbolError(), 422, "Desteklenmeyen BIST sembolü."),
        (StrategyPretestError(), 422, "Strateji güvenli doğrulama aşamalarını geçemedi."),
        (
            FrozenStrategyExecutionError(),
            422,
            "Üretilen strateji gerçek test verisi üzerinde çalıştırılamadı.",
        ),
        (NvidiaNimError("secret"), 502, "Strateji şu anda oluşturulamıyor."),
        (MarketDataUnavailableError("provider"), 502, "Piyasa verisi şu anda kullanılamıyor."),
        (
            SandboxUnavailableError("docker command"),
            503,
            "Güvenli strateji çalışma ortamı şu anda kullanılamıyor.",
        ),
        (RuntimeError("traceback secret"), 500, "Strategy Lab isteği şu anda tamamlanamıyor."),
    ],
)
def test_strategy_lab_errors_are_stable_and_safe(error, expected_status, expected_detail) -> None:
    class FailingService:
        async def run(self, request):
            raise error

    app.dependency_overrides[get_strategy_lab_service] = FailingService
    try:
        response = request(
            "POST",
            "/api/v1/strategy-lab/run",
            {"prompt": "Geçerli strateji isteği.", "symbol": "THYAO"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == expected_status
    assert response.json() == {"detail": expected_detail}
    assert "secret" not in response.text
    assert "docker command" not in response.text


def test_invalid_strategy_lab_request_returns_422() -> None:
    response = request(
        "POST",
        "/api/v1/strategy-lab/run",
        {"prompt": "dört", "symbol": "THYAO", "commission": 0.1},
    )
    assert response.status_code == 422
