"""Strategy Lab repair, freeze ve held-out izolasyon testleri."""

import asyncio
import hashlib

import pytest

from app.runtime.errors import FrozenStrategyExecutionError, StrategyPretestError
from app.llm.repair_context import RepairFailureContext
from app.runtime.models import (
    SANDBOX_SCHEMA_VERSION,
    SafeFailureType,
    SandboxErrorCode,
    SandboxResult,
)
from app.schemas.backtest import BacktestMetrics
from app.schemas.strategy import StrategyGenerateResponse
from app.schemas.strategy_lab import StrategyLabRunRequest
from app.services.strategy_lab_service import StrategyLabService
from app.services.validation_service import ValidationService

VALID_CODE = """\
from backtesting import Strategy

class GeneratedStrategy(Strategy):
    def init(self):
        pass

    def next(self):
        pass
"""
INVALID_CODE = VALID_CODE + '\nprint("not allowed")\n'


def metrics() -> BacktestMetrics:
    return BacktestMetrics(
        initial_cash=100_000,
        final_equity=101_000,
        net_profit=1_000,
        return_percent=1,
        buy_and_hold_return_percent=2,
        number_of_trades=1,
        win_rate_percent=100,
        max_drawdown_percent=-1,
        sharpe_ratio=1,
        sortino_ratio=1.2,
        profit_factor=2,
        best_trade_percent=1,
        worst_trade_percent=1,
        average_trade_duration="2 days 00:00:00",
        exposure_time_percent=10,
    )


def result(
    stage: str,
    code_hash: str,
    *,
    success: bool = True,
    error_code: SandboxErrorCode | None = None,
) -> SandboxResult:
    return SandboxResult(
        schema_version=SANDBOX_SCHEMA_VERSION,
        success=success,
        stage=stage,
        error_code=error_code,
        error_message=None if success else "safe",
        safe_failure_type=(
            SafeFailureType.ATTRIBUTE_ERROR
            if not success and error_code == SandboxErrorCode.STRATEGY_RUNTIME_ERROR
            else None
        ),
        strategy_code_hash=code_hash,
        metrics=metrics() if stage == "backtest" and success else None,
        duration_seconds=0.01,
    )


class FakeStrategyService:
    def __init__(self, versions: list[str]) -> None:
        self.versions = iter(versions)
        self.repair_calls: list[tuple[str, str, RepairFailureContext]] = []

    async def generate(self, prompt: str) -> StrategyGenerateResponse:
        return StrategyGenerateResponse(code=next(self.versions), model="test/model")

    async def repair(
        self,
        original_prompt: str,
        current_code: str,
        context: RepairFailureContext,
    ) -> StrategyGenerateResponse:
        self.repair_calls.append((original_prompt, current_code, context))
        return StrategyGenerateResponse(code=next(self.versions), model="test/model")


class FakeSandbox:
    def __init__(self, smoke_failures: int = 0, backtest_success: bool = True) -> None:
        self.smoke_failures = smoke_failures
        self.backtest_success = backtest_success
        self.smoke_calls: list[tuple[str, str]] = []
        self.backtest_calls: list[tuple[str, str, object]] = []

    def run_smoke(self, code, code_hash, initial_cash, commission) -> SandboxResult:
        self.smoke_calls.append((code, code_hash))
        if len(self.smoke_calls) <= self.smoke_failures:
            return result(
                "smoke",
                code_hash,
                success=False,
                error_code=SandboxErrorCode.STRATEGY_RUNTIME_ERROR,
            )
        return result("smoke", code_hash)

    def run_backtest(
        self, code, code_hash, data, initial_cash, commission
    ) -> SandboxResult:
        self.backtest_calls.append((code, code_hash, data.copy()))
        if not self.backtest_success:
            return result(
                "backtest",
                code_hash,
                success=False,
                error_code=SandboxErrorCode.STRATEGY_RUNTIME_ERROR,
            )
        return result("backtest", code_hash)


class FakeMarketProvider:
    def __init__(self, data) -> None:
        self.data = data
        self.calls: list[str] = []

    def download_daily(self, yahoo_symbol: str):
        self.calls.append(yahoo_symbol)
        return self.data.copy()


def request() -> StrategyLabRunRequest:
    return StrategyLabRunRequest(
        prompt="RSI düşükken al ve yüksekken sat.",
        symbol="THYAO",
    )


def build_service(strategy, sandbox, provider, observer=None) -> StrategyLabService:
    return StrategyLabService(
        strategy,
        ValidationService(),
        sandbox,
        provider,
        max_strategy_versions=3,
        observer=observer,
    )


class RecordingObserver:
    def __init__(self) -> None:
        self.events = []

    def on_generated(self, attempt, source, generated) -> None:
        self.events.append(("generated", attempt, source, generated.code))

    def on_validation(self, attempt, code, validation) -> None:
        self.events.append(("validation", attempt, validation.valid))

    def on_smoke(self, attempt, result) -> None:
        self.events.append(("smoke", attempt, result.success))

    def on_repair_requested(self, failed_attempt, next_attempt, context) -> None:
        self.events.append(
            ("repair", failed_attempt, next_attempt, context.failure_type)
        )

    def on_backtest(self, result) -> None:
        self.events.append(("backtest", result.success))


def test_first_version_freezes_and_runs_identical_code(ohlcv_data) -> None:
    strategy = FakeStrategyService([VALID_CODE])
    sandbox = FakeSandbox()
    provider = FakeMarketProvider(ohlcv_data)

    response = asyncio.run(build_service(strategy, sandbox, provider).run(request()))

    assert response.generation.attempt_count == 1
    assert response.generation.repaired is False
    assert sandbox.smoke_calls[0][0] == sandbox.backtest_calls[0][0] == VALID_CODE.strip()
    expected_hash = hashlib.sha256(VALID_CODE.strip().encode()).hexdigest()
    assert sandbox.smoke_calls[0][1] == sandbox.backtest_calls[0][1] == expected_hash
    assert provider.calls == ["THYAO.IS"]


def test_static_failure_repairs_before_market_and_reports_metadata(ohlcv_data) -> None:
    strategy = FakeStrategyService([INVALID_CODE, VALID_CODE])
    sandbox = FakeSandbox()
    provider = FakeMarketProvider(ohlcv_data)

    response = asyncio.run(build_service(strategy, sandbox, provider).run(request()))

    assert response.generation.attempt_count == 2
    assert response.generation.repaired is True
    assert len(strategy.repair_calls) == 1
    repair_call = strategy.repair_calls[0]
    assert "Yasaklı fonksiyon çağrısı: print" in repair_call[2].safe_findings
    assert repair_call[2].stage == "static"
    assert "SecurityValidationError" in repair_call[2].failure_type
    assert "2026-06-30" not in repr(repair_call)
    assert "THYAO.IS" not in repr(repair_call)
    assert provider.calls == ["THYAO.IS"]


def test_smoke_failure_can_repair_but_market_data_is_not_leaked(ohlcv_data) -> None:
    strategy = FakeStrategyService([VALID_CODE, VALID_CODE + "\n# repaired"])
    sandbox = FakeSandbox(smoke_failures=1)
    provider = FakeMarketProvider(ohlcv_data)

    response = asyncio.run(build_service(strategy, sandbox, provider).run(request()))

    assert response.generation.attempt_count == 2
    assert response.generation.repaired is True
    repair_context = strategy.repair_calls[0][2]
    assert repair_context.stage == "smoke"
    assert repair_context.failure_type == "AttributeError"
    assert repair_context.family == "unknown"
    assert repair_context.safe_findings == ("Strategy failed during isolated smoke execution.",)
    assert "pandas.Series" not in str(repair_context.compatibility_guidance)
    assert provider.calls == ["THYAO.IS"]


def test_three_invalid_versions_stop_before_market(ohlcv_data) -> None:
    strategy = FakeStrategyService([INVALID_CODE, INVALID_CODE, INVALID_CODE])
    sandbox = FakeSandbox()
    provider = FakeMarketProvider(ohlcv_data)

    with pytest.raises(StrategyPretestError):
        asyncio.run(build_service(strategy, sandbox, provider).run(request()))

    assert len(strategy.repair_calls) == 2
    assert sandbox.smoke_calls == []
    assert provider.calls == []


def test_filesystem_versions_never_reach_smoke_market_or_backtest(ohlcv_data) -> None:
    versions = [
        VALID_CODE + "\nreader = open\nreader('unused')",
        "import pandas as pd\n" + VALID_CODE + "\nreader = pd.read_csv\nreader('unused')",
        "import pandas as pd\n" + VALID_CODE + "\nframe = pd.DataFrame()\nwriter = frame.to_csv\nwriter('unused')",
    ]
    strategy = FakeStrategyService(versions)
    sandbox = FakeSandbox()
    provider = FakeMarketProvider(ohlcv_data)
    with pytest.raises(StrategyPretestError):
        asyncio.run(build_service(strategy, sandbox, provider).run(request()))
    assert len(strategy.repair_calls) == 2
    assert all(context.stage == "static" for _, _, context in strategy.repair_calls)
    assert sandbox.smoke_calls == []
    assert sandbox.backtest_calls == []
    assert provider.calls == []


def test_real_held_out_failure_never_repairs_or_reruns(ohlcv_data) -> None:
    strategy = FakeStrategyService([VALID_CODE, VALID_CODE + "\n# must not be used"])
    sandbox = FakeSandbox(backtest_success=False)
    provider = FakeMarketProvider(ohlcv_data)

    with pytest.raises(FrozenStrategyExecutionError):
        asyncio.run(build_service(strategy, sandbox, provider).run(request()))

    assert strategy.repair_calls == []
    assert len(sandbox.smoke_calls) == 1
    assert len(sandbox.backtest_calls) == 1
    assert sandbox.smoke_calls[0][:2] == sandbox.backtest_calls[0][:2]


def test_observer_records_attempt_lifecycle_without_changing_response(ohlcv_data) -> None:
    strategy = FakeStrategyService([VALID_CODE, VALID_CODE + "\n# repaired"])
    sandbox = FakeSandbox(smoke_failures=1)
    provider = FakeMarketProvider(ohlcv_data)
    observer = RecordingObserver()

    response = asyncio.run(
        build_service(strategy, sandbox, provider, observer=observer).run(request())
    )

    assert response.status == "success"
    assert [event[0] for event in observer.events] == [
        "generated",
        "validation",
        "smoke",
        "repair",
        "generated",
        "validation",
        "smoke",
        "backtest",
    ]
    assert observer.events[3] == ("repair", 1, 2, "AttributeError")
