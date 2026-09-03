"""Probes must diagnose the configured model without retrying or leaking secrets."""

import asyncio
import json
from types import SimpleNamespace

import httpx
from openai import AuthenticationError

from app.config import Settings
from app.llm.nvidia_options import get_model_options
from scripts import check_nvidia_connection as diagnostic


def test_model_profile_is_isolated_and_bounded() -> None:
    model = "deepseek-ai/deepseek-v4-pro-0813"
    first = get_model_options(model)
    first["extra_body"]["chat_template_kwargs"]["thinking"] = True
    assert get_model_options(model)["extra_body"] == {
        "chat_template_kwargs": {"thinking": False}
    }
    assert "max_tokens" not in get_model_options(model)
    assert get_model_options("other/model") == {"temperature": 0.1}


def install_fake(monkeypatch, *, error=None):
    calls = []
    settings = Settings(_env_file=None, nvidia_api_key="nvapi-diagnostic-secret",
                        nvidia_model="deepseek-ai/deepseek-v4-pro-0813")
    monkeypatch.setattr(diagnostic, "get_settings", lambda: settings)

    class Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(
                with_raw_response=SimpleNamespace(create=self.create)))
            assert kwargs["max_retries"] == 0
            assert kwargs["timeout"].connect == 15

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def create(self, **kwargs):
            calls.append(kwargs)
            if error:
                raise error
            content = "OK" if len(calls) == 1 else "def add(a, b): return a + b"
            completion = SimpleNamespace(model="returned/model", choices=[
                SimpleNamespace(message=SimpleNamespace(content=content), finish_reason="stop")])
            return SimpleNamespace(status_code=200, parse=lambda: completion)

    monkeypatch.setattr(diagnostic, "AsyncOpenAI", Client)
    return calls


def test_probes_use_configured_model_and_report_actual_response(monkeypatch, capsys):
    calls = install_fake(monkeypatch)
    assert asyncio.run(diagnostic.check_connection()) == 0
    assert [call["max_tokens"] for call in calls] == [32, 512]
    assert all(call["stream"] is False for call in calls)
    assert all(call["model"] == "deepseek-ai/deepseek-v4-pro-0813" for call in calls)
    assert all(call["extra_body"]["chat_template_kwargs"]["thinking"] is False for call in calls)
    records = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert all(record["returned_model"] == "returned/model" for record in records[1:])
    assert all(record["duration_seconds"] >= 0 for record in records[1:])


def test_failed_probe_stops_without_printing_provider_body(monkeypatch, capsys):
    error = AuthenticationError("nvapi-diagnostic-secret raw provider payload", response=httpx.Response(
        401, request=httpx.Request("POST", "https://example.test")), body=None)
    calls = install_fake(monkeypatch, error=error)
    assert asyncio.run(diagnostic.check_connection()) == 1
    assert len(calls) == 1
    output = capsys.readouterr().out
    assert "nvapi-diagnostic-secret" not in output
    assert "raw provider payload" not in output
    assert json.loads(output.splitlines()[-1])["http_status"] == 401
