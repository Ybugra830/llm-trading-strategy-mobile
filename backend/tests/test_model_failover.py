"""Stage-specific provider policy, with no external NVIDIA calls."""

import asyncio
from time import perf_counter
from contextlib import asynccontextmanager
from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APIStatusError, APITimeoutError

from app.api.strategy_routes import get_strategy_service
from app.api.strategy_lab_routes import get_strategy_lab_service
from app.config import Settings
from app.llm.nvidia_client import NvidiaNimClient, NvidiaNimError, ProviderErrorKind
from app.llm.repair_context import RepairFailureContext

SECRET = "nvapi-private-test-marker"
CONTEXT = RepairFailureContext("static", "syntax", (), ("Syntax error",), ())


def settings(**updates):
    return Settings(_env_file=None, nvidia_api_key=SECRET, nvidia_model="test/primary",
                    nvidia_fallback_model="test/fallback", nvidia_retry_backoff_seconds=0,
                    **updates)


def error(kind):
    request = httpx.Request("POST", "https://example.invalid/v1")
    if kind == "timeout":
        return APITimeoutError(request=request)
    if kind == "network":
        return APIConnectionError(message=SECRET, request=request)
    return APIStatusError(SECRET, response=httpx.Response(kind, request=request), body={"secret": SECRET})


class Boundary:
    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.calls = []
        self.closed = False
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        if outcome == "hang":
            await asyncio.sleep(10)
        return SimpleNamespace(model="actual/" + kwargs["model"].split("/")[-1],
                               choices=[SimpleNamespace(message=SimpleNamespace(content="{}"))])

    async def close(self):
        self.closed = True


async def invoke(provider, stage):
    if stage == "assessment":
        return await provider.assess_intent("input")
    if stage == "generation":
        return await provider.generate_code("input")
    return await provider.repair_code("input", "code", CONTEXT)


@pytest.mark.parametrize("stage", ["assessment", "generation", "repair"])
@pytest.mark.parametrize("failure,retries,fallback,kind", [
    (None, 0, False, None),
    (404, 0, True, ProviderErrorKind.MODEL_UNAVAILABLE),
    (410, 0, True, ProviderErrorKind.MODEL_UNAVAILABLE),
    ("timeout", 1, True, ProviderErrorKind.TIMEOUT),
    (429, 1, False, ProviderErrorKind.RATE_LIMIT),
    (503, 1, False, ProviderErrorKind.SERVER),
    (401, 0, False, ProviderErrorKind.AUTHENTICATION),
    (403, 0, False, ProviderErrorKind.PERMISSION),
    (400, 0, False, ProviderErrorKind.INVALID_REQUEST),
    ("network", 0, False, ProviderErrorKind.NETWORK),
])
def test_policy_for_each_stage(monkeypatch, caplog, stage, failure, retries, fallback, kind):
    caplog.set_level("INFO", logger="app.llm.nvidia_client")
    outcomes = ["ok"] if failure is None else [error(failure)] * (1 + retries) + ["ok"]
    boundary = Boundary(outcomes)
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: boundary)
    expected_fallback = fallback

    async def run():
        async with NvidiaNimClient(settings()) as provider:
            if failure is not None and not expected_fallback:
                with pytest.raises(NvidiaNimError) as caught:
                    await invoke(provider, stage)
                assert caught.value.kind == kind
                assert SECRET not in str(caught.value)
            else:
                assert await invoke(provider, stage) == "{}"
                assert provider.model == ("actual/fallback" if expected_fallback else "actual/primary")

    asyncio.run(run())
    expected = ["test/primary"] * (1 + retries)
    if expected_fallback:
        expected.append("test/fallback")
        assert boundary.calls[0]["messages"] == boundary.calls[-1]["messages"]
    assert [c["model"] for c in boundary.calls] == expected
    assert boundary.closed
    assert SECRET not in caplog.text
    if failure is None or expected_fallback:
        assert f"returned_model=actual/{'fallback' if expected_fallback else 'primary'}" in caplog.text


@pytest.mark.parametrize("stage", ["assessment", "generation", "repair"])
def test_both_models_fail_once_without_recursion(monkeypatch, stage):
    boundary = Boundary([error(404), error(410)])
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: boundary)
    with pytest.raises(NvidiaNimError) as caught:
        asyncio.run(invoke(NvidiaNimClient(settings()), stage))
    assert caught.value.kind == ProviderErrorKind.MODEL_UNAVAILABLE
    assert SECRET not in str(caught.value)
    assert [c["model"] for c in boundary.calls] == ["test/primary", "test/fallback"]
    assert boundary.closed


@pytest.mark.parametrize("stage", ["assessment", "generation", "repair"])
def test_stage_deadline_cancels_calls_and_bounds_both_models(monkeypatch, stage):
    boundary = Boundary(["hang", "hang"])
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: boundary)
    configured = settings().model_copy(update={"nvidia_request_timeout_seconds": 0.2})
    started = perf_counter()
    with pytest.raises(NvidiaNimError) as caught:
        asyncio.run(invoke(NvidiaNimClient(configured), stage))
    assert caught.value.kind == ProviderErrorKind.TIMEOUT
    assert len(boundary.calls) == 2
    assert boundary.closed
    assert perf_counter() - started < 0.35


@pytest.mark.parametrize("lab", [False, True])
def test_concurrent_request_dependencies_have_independent_model_metadata(monkeypatch, lab):
    constructed = []

    def factory(**kwargs):
        # First request falls back, second succeeds at primary.
        boundary = Boundary([error(404), "ok"] if not constructed else ["ok"])
        constructed.append(boundary)
        return boundary

    monkeypatch.setattr("app.api.strategy_routes.get_settings", settings)
    monkeypatch.setattr("app.api.strategy_lab_routes.get_settings", settings)
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", factory)

    async def run():
        dependency = asynccontextmanager(get_strategy_lab_service if lab else get_strategy_service)
        async with dependency() as first, dependency() as second:
            if lab:
                first, second = first._strategy_service, second._strategy_service
            assert first._client is not second._client
            await asyncio.gather(first._client.generate_code("first"), second._client.generate_code("second"))
            assert first._client.model == "actual/fallback"
            assert second._client.model == "actual/primary"

    asyncio.run(run())
    assert len(constructed) == 2
    assert all(c.closed for c in constructed)


@pytest.mark.parametrize("stage", ["assessment", "generation", "repair"])
@pytest.mark.parametrize("fallback", [None, "test/primary"])
def test_missing_or_identical_fallback_never_repeats_primary(monkeypatch, stage, fallback):
    boundary = Boundary([error(404)])
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: boundary)
    configured = settings().model_copy(update={"nvidia_fallback_model": fallback})
    with pytest.raises(NvidiaNimError):
        asyncio.run(invoke(NvidiaNimClient(configured), stage))
    assert len(boundary.calls) == 1


@pytest.mark.parametrize("stage", ["assessment", "generation", "repair"])
def test_early_failure_gives_fallback_the_original_deadline(monkeypatch, stage):
    deadlines = []

    async def complete(self, messages, model, *, deadline, max_tokens, stage):
        deadlines.append((model, deadline, max_tokens))
        if model == "test/primary":
            raise NvidiaNimError("Safe", kind=ProviderErrorKind.MODEL_UNAVAILABLE)
        return "{}"

    boundary = Boundary([])
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: boundary)
    monkeypatch.setattr(NvidiaNimClient, "_complete_model", complete)
    configured = settings(nvidia_request_timeout_seconds=60, nvidia_max_tokens=4096)
    assert asyncio.run(invoke(NvidiaNimClient(configured), stage)) == "{}"
    assert deadlines[1][1] - deadlines[0][1] == pytest.approx(15 if stage == "assessment" else 30)
    assert deadlines[1][2] == (2048 if stage == "assessment" else 4096)


@pytest.mark.parametrize("decision", ["rejected", "needs_clarification"])
def test_valid_nonacceptance_never_calls_fallback(monkeypatch, decision):
    import json
    from app.services.admission_service import StrategyAdmissionService, StrategyAdmissionError
    from tests.test_strategy_admission import refused

    class Nonacceptance(Boundary):
        async def create(self, **kwargs):
            self.calls.append(kwargs)
            payload = refused(decision, "non_strategy" if decision == "rejected" else "incomplete",
                              [] if decision == "rejected" else ["entry_rule", "exit_rule"])
            return SimpleNamespace(model="actual/primary", choices=[
                SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])

    boundary = Nonacceptance([])
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: boundary)
    with pytest.raises(StrategyAdmissionError) as caught:
        asyncio.run(StrategyAdmissionService(NvidiaNimClient(settings())).assess("RSI"))
    assert caught.value.failure.decision == decision
    assert len(boundary.calls) == 1


def test_nemotron_profiles_do_not_inherit_gpt_reasoning_parameters():
    from app.llm.nvidia_options import get_model_options
    for model in ("nvidia/nemotron-3-super-120b-a12b", "mistralai/mistral-nemotron"):
        assert "reasoning_effort" not in get_model_options(model)


@pytest.mark.parametrize("stage", ["assessment", "generation", "repair"])
def test_timeout_retry_backoff_uses_primary_slice_then_remaining_budget(monkeypatch, stage):
    boundary = Boundary([error("timeout"), "ok"])
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: boundary)
    configured = settings().model_copy(update={"nvidia_request_timeout_seconds": 0.2,
                                              "nvidia_retry_backoff_seconds": 1})
    started = perf_counter()
    assert asyncio.run(invoke(NvidiaNimClient(configured), stage)) == "{}"
    assert [c["model"] for c in boundary.calls] == ["test/primary", "test/fallback"]
    assert perf_counter() - started < 0.35
