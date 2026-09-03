"""Safe metadata classification and strict v3 sandbox identity checks."""
import asyncio
import json

import pytest
from backtesting.backtesting import Position, Trade

from sandbox.worker import safe_runtime_context
from app.runtime.docker_executor import DockerSandboxExecutor
from app.runtime.errors import SandboxProtocolError
from app.runtime.models import SafeFailureContext
from app.llm.repair_context import build_repair_context
from tests.test_strategy_lab_service import (FakeStrategyService, FakeSandbox, FakeMarketProvider, VALID_CODE, build_service, request)


def metadata_error(obj, name):
    try:
        getattr(obj, name)
    except AttributeError as error:
        return error
    raise AssertionError("attribute must not exist")


@pytest.mark.parametrize("obj,attribute,finding,api", [
    (Position(None), "entry_price", "invalid_position_attribute", "Position.entry_price"),
    (Position(None), "nvapi_SECRET_unknown", "invalid_position_attribute", "Position.unsupported_attribute"),
    (object.__new__(Trade), "nvapi_SECRET_unknown", "invalid_trade_attribute", "Trade.unsupported_attribute"),
])
def test_real_object_metadata_is_sanitized(obj, attribute, finding, api):
    context = safe_runtime_context(metadata_error(obj, attribute))
    assert context == {"family": "position_management", "finding": finding, "api": api}
    assert "SECRET" not in json.dumps(context)
    outer = RuntimeError("raw traceback or provider details must never cross")
    outer.__cause__ = metadata_error(obj, attribute)
    assert safe_runtime_context(outer) == context


def test_exception_message_cannot_spoof_position_context():
    assert safe_runtime_context(AttributeError("Position.entry_price secret")) is None
    assert safe_runtime_context(metadata_error(object(), "entry_price")) is None


def payload():
    return dict(schema_version=3, stage="smoke", success=False, error_code="STRATEGY_RUNTIME_ERROR",
                safe_failure_type="AttributeError", strategy_code_hash="a" * 64, duration_seconds=.01,
                safe_failure_context=dict(family="position_management", finding="invalid_position_attribute", api="Position.entry_price"))


@pytest.mark.parametrize("patch", [
    {"schema_version": 2}, {"stage": "backtest"}, {"strategy_code_hash": "b" * 64}, {"success": "false"},
    {"schema_version": 3.0}, {"duration_seconds": "0.01"}, {"duration_seconds": True},
    {"safe_failure_type": "secret"}, {"safe_failure_type": "TypeError"},
    {"safe_failure_context": {"family": "position_management", "finding": "secret", "api": "Position.entry_price"}},
    {"safe_failure_context": {"family": "indicator_adapter", "finding": "invalid_position_attribute", "api": "Position.entry_price"}},
    {"safe_failure_context": {"family": 3}}, {"traceback": "secret"},
])
def test_invalid_protocol_and_identity_fail_closed(patch):
    value = payload() | patch
    with pytest.raises(SandboxProtocolError):
        DockerSandboxExecutor._parse_result(json.dumps(value).encode(), "smoke", "a" * 64)


def test_context_optional_but_version_not_optional():
    value = payload()
    value.pop("safe_failure_context")
    assert DockerSandboxExecutor._parse_result(json.dumps(value).encode(), "smoke", "a" * 64).safe_failure_context is None


def test_position_repair_excludes_indicator_and_raw_context():
    context = build_repair_context(stage="smoke", failure_type="AttributeError", code="RSIIndicator", prompt="RSI",
        safe_findings=["SECRET traceback docker run provider raw"], runtime_context=SafeFailureContext(**payload()["safe_failure_context"]))
    assert context.family == "position_management"
    assert context.safe_findings == ("Invalid position attribute.",)
    text = str(context.compatibility_guidance)
    assert "Trade.entry_price" in text and "Trade.sl is writable" in text
    assert "pandas" not in text and "self.I" not in text and "SECRET" not in str(context)


def test_service_passes_real_safe_context_into_repair(ohlcv_data):
    class PositionFailureSandbox(FakeSandbox):
        def run_smoke(self, *args):
            result = super().run_smoke(*args)
            if not result.success:
                return result.model_copy(update={"safe_failure_context": SafeFailureContext(**payload()["safe_failure_context"])})
            return result
    strategy = FakeStrategyService([VALID_CODE, VALID_CODE])
    asyncio.run(build_service(strategy, PositionFailureSandbox(smoke_failures=1), FakeMarketProvider(ohlcv_data)).run(request()))
    context = strategy.repair_calls[0][2]
    assert context.stage == "smoke" and context.family == "position_management"
    assert "pandas" not in str(context.compatibility_guidance)
