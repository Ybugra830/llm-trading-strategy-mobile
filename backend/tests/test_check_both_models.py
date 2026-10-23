"""Real SDK parsing over a mock HTTP boundary; diagnostic never calls NVIDIA."""

import asyncio
import json

import httpx
from openai import AsyncOpenAI

from scripts.check_both_models import MESSAGES, probe


def completion(content="OK", finish="stop"):
    return {"id": "test", "object": "chat.completion", "created": 0, "model": "test/model",
            "choices": [{"index": 0, "finish_reason": finish,
                         "message": {"role": "assistant", "content": content}}]}


def execute(responses, model="test/model"):
    calls = []
    responses = iter(responses)

    def respond(request):
        calls.append(json.loads(request.content))
        item = next(responses)
        if isinstance(item, Exception):
            raise item
        return item

    async def run():
        async with AsyncOpenAI(api_key="private-test-key", base_url="https://example.invalid/v1",
                               max_retries=0,
                               http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond))) as client:
            result = await probe(client, "primary", model, 5)
            http_client = client._client
        assert http_client.is_closed
        return result.summary()

    return asyncio.run(run()), calls


def test_success_uses_exact_messages_and_one_ten_token_request():
    result, calls = execute([httpx.Response(200, json=completion())])
    assert result["api_accessible"] and result["ok_verified"]
    assert not result["extra_attempt"]
    assert calls[0]["messages"] == MESSAGES
    assert calls[0]["max_tokens"] == 10
    assert result["attempts"][0]["finish_reason"] == "stop"


def test_empty_truncated_response_is_accessible_and_gets_one_larger_budget():
    result, calls = execute([httpx.Response(200, json=completion(None, "length")),
                             httpx.Response(200, json=completion())])
    assert result["api_accessible"] and result["ok_verified"]
    assert [c["max_tokens"] for c in calls] == [10, 512]
    assert result["attempts"][0]["empty_content"]
    assert result["extra_attempt"]


def test_second_empty_response_does_not_loop_or_label_down():
    result, calls = execute([httpx.Response(200, json=completion(None, "length"))] * 2)
    assert result["api_accessible"] and not result["ok_verified"]
    assert len(calls) == 2
    assert "DOWN" not in json.dumps(result)


def test_explicit_unsupported_parameter_gets_one_retry_without_profile():
    result, calls = execute([httpx.Response(400, json={"error": {"code": "unsupported_parameter"}}),
                             httpx.Response(200, json=completion())])
    assert result["attempts"][0]["unsupported_parameters"]
    assert "temperature" in calls[0] and "temperature" not in calls[1]
    assert result["ok_verified"]


def test_generic_400_is_not_assumed_unsupported_or_retried():
    result, calls = execute([httpx.Response(400, json={"error": {"message": "secret-body"}})])
    assert len(calls) == 1
    assert not result["attempts"][0]["unsupported_parameters"]
    assert "secret-body" not in json.dumps(result)


def test_finished_non_ok_is_not_access_failure_or_retried():
    result, calls = execute([httpx.Response(200, json=completion("hello"))])
    assert result["api_accessible"] and not result["ok_verified"]
    assert len(calls) == 1


def test_missing_fallback_does_not_invent_model_or_call_api():
    result, calls = execute([], model=None)
    assert result["status"] == "not_configured" and calls == []


def test_http_errors_do_not_retry_or_disclose_body():
    for status in (401, 403, 404, 429, 503):
        result, calls = execute([httpx.Response(status, json={"error": {"message": "private-test-key"}})])
        assert len(calls) == 1 and not result["api_accessible"]
        assert result["attempts"][0]["http_status"] == status
        assert "private-test-key" not in json.dumps(result)


def test_timeout_and_network_errors_are_safe_and_not_retried():
    for exception in (httpx.ReadTimeout("secret-url"), httpx.ConnectError("secret-url")):
        result, calls = execute([exception])
        assert len(calls) == 1 and not result["api_accessible"]
        assert result["attempts"][0]["error_kind"] in {"provider_timeout", "network_failure"}
        assert "secret-url" not in json.dumps(result)


def test_direct_models_run_independently_and_one_failure_does_not_mask_other(monkeypatch):
    from app.config import Settings
    from scripts.check_both_models import run

    calls, clients = [], []

    def respond(request):
        payload = json.loads(request.content)
        calls.append(payload)
        if payload["model"] == "test/primary":
            return httpx.Response(401, json={"error": {"message": "private-test-key"}})
        return httpx.Response(200, json=completion())

    def factory(**kwargs):
        assert kwargs["max_retries"] == 0
        client = AsyncOpenAI(**kwargs, http_client=httpx.AsyncClient(transport=httpx.MockTransport(respond)))
        clients.append(client)
        return client

    monkeypatch.setattr("scripts.check_both_models.AsyncOpenAI", factory)
    configured = Settings(_env_file=None, nvidia_api_key="private-test-key", nvidia_model="test/primary",
                          nvidia_fallback_model="test/fallback")
    primary, fallback = asyncio.run(run(configured))
    assert not primary.summary()["ok_verified"] and fallback.summary()["ok_verified"]
    assert sorted(c["model"] for c in calls) == ["test/fallback", "test/primary"]
    assert clients[0].is_closed()
