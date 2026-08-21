"""NVIDIA NIM istemcisinin ağdan bağımsız testleri."""

import asyncio
import logging
from types import SimpleNamespace

import httpx
import pytest
from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
)

from app.config import Settings
from app.llm.nvidia_client import NvidiaNimClient, NvidiaNimError

TEST_API_KEY = "nvapi-test-secret-value"


class FakeAsyncOpenAI:
    """AsyncOpenAI bağlamını ve completion çağrısını taklit eder."""

    def __init__(self, *, error: OpenAIError | None = None, **kwargs) -> None:
        self.error = error
        self.client_kwargs = kwargs
        self.create_kwargs: dict = {}
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self.create_completion)
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def create_completion(self, **kwargs):
        self.create_kwargs = kwargs
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
    }
    assert fake_client.create_kwargs["model"] == "openai/gpt-oss-20b"
    assert fake_client.create_kwargs["temperature"] == 0.1
    assert fake_client.create_kwargs["max_tokens"] == 2048
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
            ["GeneratedStrategy arayüzü eksik."],
        )
    )

    assert result == "generated code"
    content = fake_client.create_kwargs["messages"][1]["content"]
    assert "RSI düşükken al." in content
    assert "class GeneratedStrategy: pass" in content
    assert "GeneratedStrategy arayüzü eksik." in content
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
    assert "[REDACTED]" in caplog.text or isinstance(provider_error, APITimeoutError)


def test_missing_api_key_does_not_create_sdk_client(monkeypatch) -> None:
    def fail_if_called(**kwargs):
        raise AssertionError("AsyncOpenAI should not be created without an API key")

    monkeypatch.setattr("app.llm.nvidia_client.AsyncOpenAI", fail_if_called)

    with pytest.raises(NvidiaNimError, match="API anahtarı"):
        asyncio.run(NvidiaNimClient(build_settings(api_key="")).generate_code("test"))
