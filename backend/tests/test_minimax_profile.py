"""Installed SDK wire test; no provider network calls."""
import asyncio
import json

import httpx
from openai import AsyncOpenAI

from app.config import Settings
from app.llm.nvidia_client import NvidiaNimClient
from app.llm.nvidia_options import get_model_options


def test_minimax_wire_profile_preserves_primary_and_limits(monkeypatch):
    model = 'minimaxai/minimax-m3.1-flash'
    seen = []
    sdk_options = []

    def respond(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={
            'id': 'offline-test', 'object': 'chat.completion', 'created': 0,
            'model': model, 'choices': [{'index': 0, 'finish_reason': 'stop',
                                      'message': {'role': 'assistant', 'content': '{}'}}]})

    def sdk(**kwargs):
        supplied = kwargs.pop('http_client')
        supplied._transport = httpx.MockTransport(respond)
        # Avoid environment proxy mounts in this network-free wire test.
        supplied._mounts = {}
        sdk_options.append(kwargs.copy())
        return AsyncOpenAI(**kwargs, http_client=supplied)

    monkeypatch.setattr('app.llm.nvidia_client.AsyncOpenAI', sdk)
    configured = Settings(_env_file=None, nvidia_api_key='offline-placeholder',
                          nvidia_model=model, nvidia_fallback_model=None)
    async def run():
        async with NvidiaNimClient(configured) as client:
            await client.assess_intent('asdfgg')
            http = client._http_client
        assert http.is_closed
    asyncio.run(run())
    body, = seen
    assert body['model'] == model
    assert body['temperature'] == 1 and body['top_p'] == .95
    assert body['reasoning_effort'] == 'low'
    assert body['stream'] is False and body['max_tokens'] == 2048
    assert 'chat_template_kwargs' not in body and 'extra_body' not in body
    assert json.loads(body['messages'][1]['content'])['strategy_request'] == 'asdfgg'
    assert sdk_options[0]['max_retries'] == 0
    assert get_model_options('nvidia/nemotron-3.5-super-vl-120b-a12b') == {
        'temperature': 1, 'top_p': .95,
        'extra_body': {'chat_template_kwargs': {'enable_thinking': False}}}
