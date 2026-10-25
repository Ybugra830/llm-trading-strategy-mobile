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


@pytest.fixture(autouse=True)
def offline_http_transport(monkeypatch):
    # Provider SDK is already fake: do not include real TLS-context setup in tiny deadline tests.
    monkeypatch.setattr('app.llm.nvidia_client.httpx.AsyncHTTPTransport',
                        lambda **kwargs: httpx.MockTransport(lambda request: httpx.Response(200)))


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
    ("timeout", 0, True, ProviderErrorKind.TIMEOUT),
    (429, 0, True, ProviderErrorKind.RATE_LIMIT),
    (500, 0, True, ProviderErrorKind.SERVER),
    (502, 0, True, ProviderErrorKind.SERVER),
    (503, 0, True, ProviderErrorKind.SERVER),
    (504, 0, True, ProviderErrorKind.SERVER),
    (501, 0, False, ProviderErrorKind.SERVER),
    (505, 0, False, ProviderErrorKind.SERVER),
    (422, 0, False, ProviderErrorKind.INVALID_REQUEST),
    (401, 0, False, ProviderErrorKind.AUTHENTICATION),
    (403, 0, False, ProviderErrorKind.PERMISSION),
    (400, 0, False, ProviderErrorKind.INVALID_REQUEST),
    (408, 0, False, ProviderErrorKind.INVALID_REQUEST),
    (409, 0, False, ProviderErrorKind.INVALID_REQUEST),
    ("network", 0, True, ProviderErrorKind.NETWORK),
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
@pytest.mark.parametrize("fallback", [None, "test/primary"])
def test_no_distinct_fallback_gets_full_stage_deadline(monkeypatch, stage, fallback):
    async def complete(self, messages, model, *, deadline, max_tokens, stage):
        remaining = deadline - asyncio.get_running_loop().time()
        assert remaining == pytest.approx(30 if stage == "assessment" else 180, abs=.05)
        return "{}"

    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: Boundary([]))
    monkeypatch.setattr(NvidiaNimClient, "_complete_model", complete)
    configured = settings().model_copy(update={"nvidia_fallback_model": fallback})
    assert asyncio.run(invoke(NvidiaNimClient(configured), stage)) == "{}"


@pytest.mark.parametrize("stage", ["assessment", "generation", "repair"])
@pytest.mark.parametrize("fallback", [None, "test/primary"])
@pytest.mark.parametrize("hang", [False, True])
def test_no_distinct_fallback_can_pass_half_budget_but_not_full(monkeypatch, stage, fallback, hang):
    class Slow(Boundary):
        async def create(self, **kwargs):
            await asyncio.sleep(.15)
            return await super().create(**kwargs)

    boundary = Slow(["hang" if hang else "ok"])
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: boundary)
    configured = settings().model_copy(update={"nvidia_request_timeout_seconds": .2,
                                              "nvidia_fallback_model": fallback})
    started = perf_counter()
    if hang:
        with pytest.raises(NvidiaNimError) as caught:
            asyncio.run(invoke(NvidiaNimClient(configured), stage))
        assert caught.value.kind == ProviderErrorKind.TIMEOUT
        assert .18 <= perf_counter() - started < .4
    else:
        assert asyncio.run(invoke(NvidiaNimClient(configured), stage)) == "{}"
    assert len(boundary.calls) == 1
    assert boundary.closed


@pytest.mark.parametrize("stage", ["assessment", "generation", "repair"])
@pytest.mark.parametrize("fallback", [None, "test/primary"])
@pytest.mark.parametrize("failure,kind", [(500, ProviderErrorKind.SERVER), ("timeout", ProviderErrorKind.TIMEOUT)])
def test_no_distinct_fallback_backoff_is_in_full_budget_and_keeps_error(monkeypatch, stage, fallback, failure, kind):
    boundary = Boundary([error(failure), "ok"])
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: boundary)
    configured = settings().model_copy(update={"nvidia_request_timeout_seconds": .12,
                                              "nvidia_retry_backoff_seconds": 1,
                                              "nvidia_fallback_model": fallback})
    provider = NvidiaNimClient(configured)
    with pytest.raises(NvidiaNimError) as caught:
        asyncio.run(invoke(provider, stage))
    assert caught.value.kind == kind
    assert len(boundary.calls) == 1
    record = provider.attempt_records[0]
    assert record["backoff_seconds"] > .08
    assert record["seconds"] < .3
    assert record["seconds"] >= record["request_seconds"] + record["backoff_seconds"]
    assert record["http_status"] == (500 if failure == 500 else None)


@pytest.mark.parametrize("stage", ["assessment", "generation", "repair"])
def test_early_failure_gives_fallback_the_original_deadline(monkeypatch, stage):
    deadlines = []

    async def complete(self, messages, model, *, deadline, max_tokens, stage):
        deadlines.append((model, deadline, max_tokens))
        if model == "test/primary":
            raise NvidiaNimError("Safe", kind=ProviderErrorKind.MODEL_UNAVAILABLE, status_code=404)
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
    for model in ("nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-3.5-super-vl-120b-a12b", "mistralai/mistral-nemotron"):
        assert "reasoning_effort" not in get_model_options(model)


def test_nemotron35_text_profile_uses_documented_sampling_and_can_disable_thinking():
    from app.llm.nvidia_options import get_model_options
    model = "nvidia/nemotron-3.5-super-vl-120b-a12b"
    expected = {"temperature": 1, "top_p": 0.95,
                "extra_body": {"chat_template_kwargs": {"enable_thinking": False}}}
    assert get_model_options(model) == expected
    options = get_model_options(model)
    options["extra_body"]["chat_template_kwargs"]["enable_thinking"] = True
    assert get_model_options(model) == expected


@pytest.mark.parametrize("stage", ["assessment", "generation", "repair"])
def test_first_timeout_uses_fallback_without_retry_or_backoff(monkeypatch, stage):
    boundary = Boundary([error("timeout"), "ok"])
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: boundary)
    configured = settings().model_copy(update={"nvidia_request_timeout_seconds": 0.2,
                                              "nvidia_retry_backoff_seconds": 1})
    started = perf_counter()
    assert asyncio.run(invoke(NvidiaNimClient(configured), stage)) == "{}"
    assert [c["model"] for c in boundary.calls] == ["test/primary", "test/fallback"]
    assert perf_counter() - started < 0.35


@pytest.mark.parametrize('stage', ['assessment', 'generation', 'repair'])
@pytest.mark.parametrize('fallback_error', [404, 410, 429, 500, 502, 503, 504, 'timeout', 'network'])
def test_fallback_failure_has_no_retry_or_return_to_primary(monkeypatch, stage, fallback_error):
    boundary = Boundary([error(503), error(fallback_error), 'ok'])
    monkeypatch.setattr('app.llm.nvidia_client.AsyncOpenAI', lambda **kw: boundary)
    provider = NvidiaNimClient(settings(nvidia_max_retries=1))
    with pytest.raises(NvidiaNimError):
        asyncio.run(invoke(provider, stage))
    assert [c['model'] for c in boundary.calls] == ['test/primary', 'test/fallback']
    assert all(r['backoff_seconds'] == 0 for r in provider.attempt_records)
    assert provider.attempt_records[0]['http_status'] == 503
    assert boundary.closed


@pytest.mark.parametrize('stage', ['assessment', 'generation', 'repair'])
def test_no_fallback_call_after_total_deadline(monkeypatch, stage):
    async def complete(self, messages, model, *, deadline, max_tokens, stage):
        await asyncio.sleep(.06)
        raise NvidiaNimError('Safe', kind=ProviderErrorKind.SERVER, status_code=503)
    monkeypatch.setattr(NvidiaNimClient, '_complete_model', complete)
    boundary = Boundary([])
    monkeypatch.setattr('app.llm.nvidia_client.AsyncOpenAI', lambda **kw: boundary)
    configured = settings().model_copy(update={'nvidia_request_timeout_seconds': .04})
    with pytest.raises(NvidiaNimError):
        asyncio.run(invoke(NvidiaNimClient(configured), stage))
    assert boundary.calls == []
    assert boundary.closed


@pytest.mark.parametrize('payload_kind', ['rejected', 'needs_clarification', 'bad_json', 'contradictory', 'ungrounded'])
def test_fallback_assessment_uses_same_gate_and_never_reaches_downstream(monkeypatch, payload_kind):
    import json
    from unittest.mock import Mock
    from app.main import app
    from app.services.strategy_service import StrategyService
    from app.services.strategy_lab_service import StrategyLabService
    from app.services.validation_service import ValidationService
    from tests.test_strategy_admission import refused, accepted

    payload = refused(payload_kind, 'non_strategy' if payload_kind == 'rejected' else 'incomplete',
                      [] if payload_kind == 'rejected' else ['entry_rule', 'exit_rule'])
    if payload_kind in ['contradictory', 'ungrounded']:
        payload = accepted('asdfgg')
        if payload_kind == 'contradictory':
            payload['unsupported_features'] = ['short selling']
    content = 'not JSON' if payload_kind == 'bad_json' else json.dumps(payload)

    class FallbackAssessment(Boundary):
        async def create(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs['model'] == 'test/primary':
                raise error(503)
            return SimpleNamespace(model='actual/fallback', choices=[
                SimpleNamespace(message=SimpleNamespace(content=content))])

    boundary = FallbackAssessment([])
    monkeypatch.setattr('app.llm.nvidia_client.AsyncOpenAI', lambda **kw: boundary)
    sandbox, market = Mock(), Mock()
    provider = NvidiaNimClient(settings())
    app.dependency_overrides[get_strategy_lab_service] = lambda: StrategyLabService(
        StrategyService(provider), ValidationService(), sandbox, market)
    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as api:
            return await api.post('/api/v1/strategy-lab/run', json={'prompt': 'asdfgg', 'symbol': 'THYAO'})
    try:
        response = asyncio.run(send())
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == (422 if payload_kind in ['rejected', 'needs_clarification'] else 502)
    assert [c['model'] for c in boundary.calls] == ['test/primary', 'test/fallback']
    assert sandbox.mock_calls == market.mock_calls == []
    counts = json.loads(response.headers['x-strategy-counts'])
    assert all(counts[name] == 0 for name in ['generation', 'repair', 'ast', 'smoke', 'download', 'clean', 'backtest'])
    assert boundary.closed


def test_lightning_profile_is_explicit_and_does_not_override_limits():
    from app.llm.nvidia_options import get_model_options
    options = get_model_options('nvidia/nemotron-3.5-lightning-30b-a3b')
    assert options == {'temperature': 1, 'top_p': .95,
                       'extra_body': {'chat_template_kwargs': {'enable_thinking': False}}}
    assert 'max_tokens' not in options and 'reasoning_effort' not in options


@pytest.mark.parametrize('stage', ['assessment', 'generation', 'repair'])
@pytest.mark.parametrize('content,finish', [('', 'stop'), ('partial', 'length')])
def test_invalid_fallback_content_is_not_success_or_another_model_call(monkeypatch, stage, content, finish):
    class InvalidFallback(Boundary):
        async def create(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs['model'] == 'test/primary':
                raise error(503)
            return SimpleNamespace(model='actual/fallback', choices=[SimpleNamespace(
                finish_reason=finish, message=SimpleNamespace(content=content))])
    boundary = InvalidFallback([])
    monkeypatch.setattr('app.llm.nvidia_client.AsyncOpenAI', lambda **kw: boundary)
    provider = NvidiaNimClient(settings())
    with pytest.raises(NvidiaNimError) as caught:
        asyncio.run(invoke(provider, stage))
    assert caught.value.kind == ProviderErrorKind.INVALID_RESPONSE
    assert [c['model'] for c in boundary.calls] == ['test/primary', 'test/fallback']
    assert provider.attempt_records[-1]['returned_model'] == 'actual/fallback'
    assert provider.attempt_records[-1]['error_kind'] == ProviderErrorKind.INVALID_RESPONSE.value
    assert boundary.closed


@pytest.mark.parametrize('stage,budget', [('assessment', 30), ('generation', 180), ('repair', 180)])
@pytest.mark.parametrize('fallback_hangs', [False, True])
def test_production_budget_split_through_real_client_with_virtual_clock(monkeypatch, stage, budget, fallback_hangs):
    """Real deadline code, fake SDK and monotonic clock; no 90-second wall-time wait."""
    deadlines = []
    original = NvidiaNimClient._complete_model

    async def observe(self, messages, model, *, deadline, max_tokens, stage):
        deadlines.append((model, deadline, asyncio.get_running_loop().time()))
        return await original(self, messages, model, deadline=deadline, max_tokens=max_tokens, stage=stage)

    monkeypatch.setattr(NvidiaNimClient, '_complete_model', observe)

    async def run():
        loop = asyncio.get_running_loop()
        real_time = loop.time
        offset = [0.0]
        monkeypatch.setattr(loop, 'time', lambda: real_time() + offset[0])

        class TimedBoundary(Boundary):
            async def create(self, **kwargs):
                if kwargs['model'] == 'test/primary' or fallback_hangs:
                    self.calls.append(kwargs)
                    offset[0] += budget / 2 + .001
                    await asyncio.sleep(3600)
                return await super().create(**kwargs)

        boundary = TimedBoundary(['ok'])
        monkeypatch.setattr('app.llm.nvidia_client.AsyncOpenAI', lambda **kw: boundary)
        provider = NvidiaNimClient(settings())
        if fallback_hangs:
            with pytest.raises(NvidiaNimError) as caught:
                await invoke(provider, stage)
            assert caught.value.kind == ProviderErrorKind.TIMEOUT
        else:
            assert await invoke(provider, stage) == '{}'
            assert provider.model == 'actual/fallback'
        assert [c['model'] for c in boundary.calls] == ['test/primary', 'test/fallback']
        assert boundary.closed
        assert all(r['backoff_seconds'] == 0 for r in provider.attempt_records)

    asyncio.run(run())
    assert deadlines[0][1] - deadlines[0][2] == pytest.approx(budget / 2, abs=.1)
    assert deadlines[1][1] - deadlines[0][1] == pytest.approx(budget / 2, abs=.001)
    assert deadlines[1][1] - deadlines[1][2] == pytest.approx(budget / 2, abs=.1)
