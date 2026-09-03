"""NVIDIA NIM istemcisinin ağdan bağımsız testleri."""

import asyncio
import logging
from types import SimpleNamespace

import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)

from app.config import Settings
from app.llm.nvidia_client import (
    NvidiaNimClient, NvidiaNimError, ProviderErrorKind, get_provider_error_details,
)
from app.services.strategy_service import StrategyService
from app.llm.repair_context import RepairFailureContext

TEST_API_KEY = "nvapi-test-secret-value"


class FakeAsyncOpenAI:
    """AsyncOpenAI bağlamını ve completion çağrısını taklit eder."""

    def __init__(self, *, error: OpenAIError | None = None, **kwargs) -> None:
        self.error = error
        self.client_kwargs = kwargs
        self.create_kwargs: dict = {}
        self.calls: list[dict] = []
        self.closed = False
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self.create_completion)
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def close(self) -> None:
        self.closed = True

    async def create_completion(self, **kwargs):
        self.create_kwargs = kwargs
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=" generated code "))]
        )


def build_settings(api_key: str = TEST_API_KEY) -> Settings:
    return Settings(
        _env_file=None,
        nvidia_api_key=api_key,
        nvidia_base_url="https://integrate.api.nvidia.com/v1",
        nvidia_model="openai/gpt-oss-20b",
        nvidia_max_tokens=2048,
        nvidia_retry_backoff_seconds=0,
    )


def build_status_error(error_type, status_code: int) -> OpenAIError:
    request = httpx.Request("POST", "https://integrate.api.nvidia.com/v1/chat/completions")
    response = httpx.Response(
        status_code,
        request=request,
        headers={"x-request-id": "req-test"},
    )
    return error_type(
        f"provider rejected {TEST_API_KEY}",
        response=response,
        body={"error": "test"},
    )


def test_generate_code_uses_expected_nvidia_parameters(monkeypatch) -> None:
    fake_client = FakeAsyncOpenAI()
    monkeypatch.setattr(
        "app.llm.nvidia_client.AsyncOpenAI",
        lambda **kwargs: _capture_client(fake_client, kwargs),
    )

    result = asyncio.run(NvidiaNimClient(build_settings()).generate_code("test prompt"))

    assert result == "generated code"
    assert fake_client.client_kwargs == {
        "api_key": TEST_API_KEY,
        "base_url": "https://integrate.api.nvidia.com/v1",
        "timeout": httpx.Timeout(connect=15, read=180, write=15, pool=15),
        "max_retries": 0,
    }
    assert fake_client.create_kwargs["model"] == "openai/gpt-oss-20b"
    assert fake_client.create_kwargs["temperature"] == 0.1
    assert fake_client.create_kwargs["max_tokens"] == 2048
    assert fake_client.create_kwargs["stream"] is False
    assert fake_client.closed
    assert [message["role"] for message in fake_client.create_kwargs["messages"]] == [
        "system",
        "user",
    ]


def test_repair_code_sends_only_supplied_prompt_code_and_safe_errors(monkeypatch) -> None:
    fake_client = FakeAsyncOpenAI()
    monkeypatch.setattr(
        "app.llm.nvidia_client.AsyncOpenAI",
        lambda **kwargs: _capture_client(fake_client, kwargs),
    )

    result = asyncio.run(
        NvidiaNimClient(build_settings()).repair_code(
            "RSI düşükken al.",
            "class GeneratedStrategy: pass",
            RepairFailureContext(
                stage="static",
                failure_type="InterfaceValidationError",
                indicator_families=("RSI",),
                safe_findings=("GeneratedStrategy arayüzü eksik.",),
                compatibility_guidance=("Use self.I.",),
            ),
        )
    )

    assert result == "generated code"
    content = fake_client.create_kwargs["messages"][1]["content"]
    assert "RSI düşükken al." in content
    assert "class GeneratedStrategy: pass" in content
    assert "GeneratedStrategy arayüzü eksik." in content
    assert "Failure type: InterfaceValidationError" in content
    assert "Indicator families: RSI" in content
    assert "Yahoo" not in content


def _capture_client(fake_client: FakeAsyncOpenAI, kwargs: dict) -> FakeAsyncOpenAI:
    fake_client.client_kwargs = kwargs
    return fake_client


@pytest.mark.parametrize(
    "provider_error",
    [
        build_status_error(AuthenticationError, 401),
        build_status_error(PermissionDeniedError, 403),
        build_status_error(NotFoundError, 404),
        build_status_error(BadRequestError, 400),
        build_status_error(RateLimitError, 429),
        APIConnectionError(
            message=f"connection failed for {TEST_API_KEY}",
            request=httpx.Request("POST", "https://integrate.api.nvidia.com/v1"),
        ),
        APITimeoutError(
            request=httpx.Request("POST", "https://integrate.api.nvidia.com/v1")
        ),
        OpenAIError(f"generic failure for {TEST_API_KEY}"),
    ],
    ids=["401", "403", "404", "400", "429", "connection", "timeout", "generic"],
)
def test_provider_errors_are_logged_safely_and_mapped(
    monkeypatch,
    caplog,
    provider_error: OpenAIError,
) -> None:
    monkeypatch.setattr(
        "app.llm.nvidia_client.AsyncOpenAI",
        lambda **kwargs: FakeAsyncOpenAI(error=provider_error, **kwargs),
    )

    with caplog.at_level(logging.ERROR, logger="app.llm.nvidia_client"):
        with pytest.raises(NvidiaNimError) as captured:
            asyncio.run(NvidiaNimClient(build_settings()).generate_code("test prompt"))

    assert captured.value.__cause__ is provider_error
    assert type(provider_error).__name__ in caplog.text
    assert TEST_API_KEY not in caplog.text
    assert "provider rejected" not in caplog.text
    assert "category=" in caplog.text


def test_missing_api_key_does_not_create_sdk_client(monkeypatch) -> None:
    def fail_if_called(**kwargs):
        raise AssertionError("AsyncOpenAI should not be created without an API key")

    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", fail_if_called)

    with pytest.raises(NvidiaNimError, match="API anahtarı"):
        asyncio.run(NvidiaNimClient(build_settings(api_key="")).generate_code("test"))


@pytest.mark.parametrize("status,kind,retry_count", [
    (400, ProviderErrorKind.INVALID_REQUEST, 0),
    (401, ProviderErrorKind.AUTHENTICATION, 0),
    (403, ProviderErrorKind.PERMISSION, 0),
    (404, ProviderErrorKind.MODEL_UNAVAILABLE, 0),
    (410, ProviderErrorKind.MODEL_UNAVAILABLE, 0),
    (408, ProviderErrorKind.INVALID_REQUEST, 0),
    (409, ProviderErrorKind.INVALID_REQUEST, 0),
    (422, ProviderErrorKind.INVALID_REQUEST, 0),
    (429, ProviderErrorKind.RATE_LIMIT, 1),
    (500, ProviderErrorKind.SERVER, 1),
    (503, ProviderErrorKind.SERVER, 1),
])
def test_status_retry_policy(monkeypatch, status, kind, retry_count):
    client = FakeAsyncOpenAI(error=build_status_error(APIStatusError, status))
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: client)
    with pytest.raises(NvidiaNimError) as captured:
        asyncio.run(NvidiaNimClient(build_settings()).generate_code("test prompt"))
    assert captured.value.kind == kind
    assert len(client.calls) == 1 + retry_count
    assert client.closed


def test_transport_timeout_retries_once_and_network_failure_does_not(monkeypatch):
    for error, expected, kind in (
        (APITimeoutError(request=httpx.Request("POST", "https://example.test")), 2, ProviderErrorKind.TIMEOUT),
        (APIConnectionError(request=httpx.Request("POST", "https://example.test")), 1, ProviderErrorKind.NETWORK),
    ):
        client = FakeAsyncOpenAI(error=error)
        monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: client)
        with pytest.raises(NvidiaNimError) as captured:
            asyncio.run(NvidiaNimClient(build_settings()).generate_code("test prompt"))
        assert captured.value.kind == kind
        assert len(client.calls) == expected


@pytest.mark.parametrize("status,use_fallback", [(404, True), (410, True), (400, False),
    (401, False), (403, False), (422, False), (429, False), (503, False)])
def test_fallback_is_explicit_and_reports_actual_model(monkeypatch, status, use_fallback):
    primary = "deepseek-ai/deepseek-v4-pro-0813"
    settings = build_settings().model_copy(update={
        "nvidia_model": primary, "nvidia_fallback_model": "tested/fallback",
    })

    class Client(FakeAsyncOpenAI):
        async def create_completion(self, **kwargs):
            self.calls.append(kwargs)
            if kwargs["model"] == primary:
                raise build_status_error(APIStatusError, status)
            return SimpleNamespace(model="actual/fallback", choices=[
                SimpleNamespace(message=SimpleNamespace(content="fallback code"))])

    client = Client()
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: client)
    service = StrategyService(NvidiaNimClient(settings))
    if use_fallback:
        result = asyncio.run(service.generate("test prompt"))
        assert result.code == "fallback code"
        assert result.model == "actual/fallback"
        assert [call["model"] for call in client.calls] == [primary, "tested/fallback"]
        assert client.calls[0]["messages"] == client.calls[1]["messages"]
        assert client.calls[0]["extra_body"] == {"chat_template_kwargs": {"thinking": False}}
        assert "extra_body" not in client.calls[1]
    else:
        with pytest.raises(NvidiaNimError):
            asyncio.run(service.generate("test prompt"))
        assert all(call["model"] == primary for call in client.calls)


def test_overall_deadline_cancels_hanging_provider_and_closes_client(monkeypatch):
    settings = build_settings().model_copy(update={"nvidia_request_timeout_seconds": 0.02})

    class HangingClient(FakeAsyncOpenAI):
        cancelled = False

        async def create_completion(self, **kwargs):
            self.calls.append(kwargs)
            try:
                await asyncio.sleep(10)
            except asyncio.CancelledError:
                self.cancelled = True
                raise

    client = HangingClient()
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: client)
    with pytest.raises(NvidiaNimError) as captured:
        asyncio.run(NvidiaNimClient(settings).generate_code("test prompt"))
    assert captured.value.kind == ProviderErrorKind.TIMEOUT
    assert len(client.calls) == 1
    assert client.cancelled and client.closed


def test_fallback_after_primary_deadline_has_one_separate_bounded_budget(monkeypatch):
    settings = build_settings().model_copy(update={"nvidia_request_timeout_seconds": 0.02,
                                                  "nvidia_fallback_model": "tested/fallback"})

    class Client(FakeAsyncOpenAI):
        async def create_completion(self, **kwargs):
            if kwargs["model"] == settings.nvidia_model:
                self.calls.append(kwargs)
                await asyncio.sleep(10)
            return await super().create_completion(**kwargs)

    client = Client()
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: client)
    provider = NvidiaNimClient(settings)
    assert asyncio.run(provider.generate_code("test prompt")) == "generated code"
    assert [call["model"] for call in client.calls] == [settings.nvidia_model, "tested/fallback"]
    assert provider.model == "tested/fallback"


@pytest.mark.parametrize("status,kind", [(429, ProviderErrorKind.RATE_LIMIT), (503, ProviderErrorKind.SERVER)])
def test_retry_backoff_cannot_extend_overall_budget_or_trigger_fallback(monkeypatch, status, kind):
    settings = build_settings().model_copy(update={"nvidia_request_timeout_seconds": 0.02,
                                                  "nvidia_retry_backoff_seconds": 1,
                                                  "nvidia_fallback_model": "tested/fallback"})
    client = FakeAsyncOpenAI(error=build_status_error(APIStatusError, status))
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: client)
    with pytest.raises(NvidiaNimError) as captured:
        asyncio.run(NvidiaNimClient(settings).generate_code("test prompt"))
    assert captured.value.kind == kind
    assert len(client.calls) == 1


def test_request_context_reuses_client_for_generation_and_repair(monkeypatch):
    client = FakeAsyncOpenAI()
    constructions = []

    def construct(**kwargs):
        constructions.append(kwargs)
        return client

    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", construct)

    async def run():
        async with NvidiaNimClient(build_settings()) as provider:
            await provider.generate_code("test prompt")
            assert not client.closed
            await provider.repair_code("test prompt", "code", RepairFailureContext(
                stage="static", failure_type="syntax", indicator_families=(),
                safe_findings=("Syntax error",), compatibility_guidance=()))
            assert not client.closed

    asyncio.run(run())
    assert len(constructions) == 1
    assert len(client.calls) == 2
    assert client.closed


def test_secret_request_id_is_not_logged():
    error = build_status_error(APIStatusError, 401)
    error.request_id = TEST_API_KEY
    details = get_provider_error_details(error, api_key=TEST_API_KEY)
    assert TEST_API_KEY not in details.as_text()
    assert details.request_id is None


def test_sdk_wire_request_uses_model_profile_and_one_owned_retry(monkeypatch):
    import json
    from openai import AsyncOpenAI

    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        if len(requests) == 1:
            return httpx.Response(429, json={"error": {"message": "rate limit"}})
        return httpx.Response(200, json={
            "id": "test-completion", "object": "chat.completion", "created": 0,
            "model": "actual/deepseek", "choices": [{"index": 0, "finish_reason": "stop",
            "message": {"role": "assistant", "content": "code"}}],
        })

    def construct(**kwargs):
        return AsyncOpenAI(**kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))

    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", construct)
    settings = build_settings().model_copy(update={"nvidia_model": "deepseek-ai/deepseek-v4-pro-0813"})
    result = asyncio.run(StrategyService(NvidiaNimClient(settings)).generate("test prompt"))
    assert result.model == "actual/deepseek"
    assert result.code == "code"
    assert len(requests) == 2
    assert requests[0] == requests[1]
    assert requests[0]["chat_template_kwargs"] == {"thinking": False}
    assert requests[0]["max_tokens"] == 2048
    assert requests[0]["stream"] is False


def test_external_cancellation_is_not_retried_or_used_for_fallback(monkeypatch):
    class Client(FakeAsyncOpenAI):
        async def create_completion(self, **kwargs):
            self.calls.append(kwargs)
            raise asyncio.CancelledError

    client = Client()
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: client)
    settings = build_settings().model_copy(update={"nvidia_fallback_model": "tested/fallback"})
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(NvidiaNimClient(settings).generate_code("test prompt"))
    assert len(client.calls) == 1
    assert client.closed


def test_unavailable_fallback_does_not_loop(monkeypatch):
    client = FakeAsyncOpenAI(error=build_status_error(APIStatusError, 410))
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: client)
    settings = build_settings().model_copy(update={"nvidia_fallback_model": "tested/fallback"})
    with pytest.raises(NvidiaNimError) as captured:
        asyncio.run(NvidiaNimClient(settings).generate_code("test prompt"))
    assert captured.value.kind == ProviderErrorKind.MODEL_UNAVAILABLE
    assert [call["model"] for call in client.calls] == [settings.nvidia_model, "tested/fallback"]


def test_empty_response_is_neither_retried_nor_fallen_back(monkeypatch):
    class Client(FakeAsyncOpenAI):
        async def create_completion(self, **kwargs):
            self.calls.append(kwargs)
            return SimpleNamespace(choices=[])

    client = Client()
    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", lambda **kw: client)
    settings = build_settings().model_copy(update={"nvidia_fallback_model": "tested/fallback"})
    with pytest.raises(NvidiaNimError) as captured:
        asyncio.run(NvidiaNimClient(settings).generate_code("test prompt"))
    assert captured.value.kind == ProviderErrorKind.INVALID_RESPONSE
    assert len(client.calls) == 1
