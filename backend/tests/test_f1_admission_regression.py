"""Recorded provider output; no real NVIDIA requests."""
import asyncio
import copy
import json
from pathlib import Path
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from app.api.strategy_lab_routes import get_strategy_lab_service
from app.api.strategy_routes import get_strategy_service
from app.llm.nvidia_client import NvidiaNimError, ProviderErrorKind
from app.main import app
from app.services.admission_service import StrategyAdmissionService
from app.services.strategy_lab_service import StrategyLabService
from app.services.strategy_service import StrategyService
from app.services.validation_service import ValidationService


def saved():
    return json.loads((Path(__file__).parent / 'fixtures/nemotron35_f1_bollinger.json').read_text(encoding='utf-8'))


def test_prompt_distinguishes_prohibitions_and_position_guards():
    from app.llm.admission_prompt import build_admission_messages
    fixture = saved()
    system, user = build_admission_messages(fixture['prompt'])
    assert 'features the user REQUIRES, not features they forbid' in system['content']
    assert 'Never encode position state as a price comparison such as NOT(Close = 0)' in system['content']
    assert json.loads(user['content'])['strategy_request'] == fixture['prompt']


@pytest.mark.parametrize('path', ['/api/v1/strategies/generate', '/api/v1/strategy-lab/run'])
def test_f1_conflicting_model_assessment_is_502_not_user_unsupported(path):
    fixture = saved()
    client = Mock(assess_intent=AsyncMock(return_value=json.dumps(fixture['assessment'])),
                  generate_code=AsyncMock(), repair_code=AsyncMock())
    strategy = StrategyService(client)
    sandbox, market = Mock(), Mock()
    lab = StrategyLabService(strategy, ValidationService(), sandbox, market)
    app.dependency_overrides[get_strategy_service] = lambda: strategy
    app.dependency_overrides[get_strategy_lab_service] = lambda: lab

    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as api:
            return await api.post(path, json={'prompt': fixture['prompt'], 'symbol': 'THYAO'})
    try:
        response = asyncio.run(send())
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502
    assert response.headers['x-error-code'] == 'ADMISSION_ACCEPTED_UNSUPPORTED_FEATURES'
    assert 'decision' not in response.json()
    client.generate_code.assert_not_awaited()
    client.repair_code.assert_not_awaited()
    assert sandbox.mock_calls == market.mock_calls == []


def test_f1_invented_zero_remains_invalid_even_without_unsupported_list():
    fixture = saved()
    payload = copy.deepcopy(fixture['assessment'])
    payload['unsupported_features'] = []
    client = Mock(assess_intent=AsyncMock(return_value=json.dumps(payload)))
    with pytest.raises(NvidiaNimError) as error:
        asyncio.run(StrategyAdmissionService(client).assess(fixture['prompt']))
    assert error.value.kind == ProviderErrorKind.INVALID_RESPONSE


def test_f1_market_conditions_alone_are_valid_without_automatic_acceptance():
    fixture = saved()
    payload = copy.deepcopy(fixture['assessment'])
    payload['unsupported_features'] = []
    payload['entry']['condition'] = payload['entry']['condition']['children'][0]
    client = Mock(assess_intent=AsyncMock(return_value=json.dumps(payload)))
    result = asyncio.run(StrategyAdmissionService(client).assess(fixture['prompt']))
    assert result.summary.decision == 'accepted'
    assert payload['entry']['condition']['operator'] == 'lt'
    assert payload['exit']['condition']['operator'] == 'gt'
