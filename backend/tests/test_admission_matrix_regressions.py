"""Actual admission gate; provider output fixtures only, no NVIDIA calls."""

import asyncio
import copy

import pytest

from tests.test_strategy_admission import accepted, provider, TR
from app.services.strategy_service import StrategyService
from app.services.admission_service import StrategyAdmissionError
from tests.test_strategy_admission import operand, rule


@pytest.mark.parametrize('family,parameters,outputs', [
    ('bollinger', {'window':20,'deviation':2}, ('lower','upper')),
    ('stochastic', {'window':14,'smooth_window':3}, ('k','k')),
    ('macd', {'window_fast':12,'window_slow':26,'window_signal':9}, ('line','signal')),
])
@pytest.mark.parametrize('whole_tuple_evidence', [False, True])
def test_explicit_indicator_tuple_is_not_a_decimal_period(family, parameters, outputs, whole_tuple_evidence):
    spec = family.title() + '(' + ','.join(str(v) for v in parameters.values()) + ')'
    prompt = spec + ': Close 20 altında al; Close 80 üzerinde kapat.'
    payload = accepted(prompt)
    payload['indicators'] = [dict(id='signal',family=family,role='single',evidence=spec,
        parameters=parameters,parameter_evidence={k:spec if whole_tuple_evidence else str(v) for k,v in parameters.items()})]
    payload['entry'] = rule('buy',prompt,operand('indicator',spec,reference='signal.'+outputs[0]),operand('constant','20',value=20),'lt')
    payload['exit'] = rule('close',prompt,operand('indicator',spec,reference='signal.'+outputs[1]),operand('constant','80',value=80),'gt')
    result=asyncio.run(StrategyService(provider(payload)).generate(prompt))
    assert result.admission.defaults_applied == []


def test_explicit_turkish_period_word_cannot_disappear_behind_default():
    prompt='21 periyotluk RSI 30 altında al, 70 üstünde kapat.'
    item=accepted(prompt,defaults=True)
    client=provider(item)
    with pytest.raises(StrategyAdmissionError):
        asyncio.run(StrategyService(client).generate(prompt))
    client.generate_code.assert_not_awaited()


def test_impossible_rsi_conjunction_requests_clarification_even_if_model_accepts():
    prompt = 'RSI14 aynı anda 30 altında VE 70 üstündeyse al; RSI14 70 üstündeyse kapat.'
    item = accepted(prompt)
    first = item['entry']['condition']
    second = copy.deepcopy(first)
    second['operator'] = 'gt'
    second['right'].update(value=70, evidence='70')
    item['entry']['condition'] = dict(operator='and', left=None, right=None, children=[first, second])
    client = provider(item)
    with pytest.raises(StrategyAdmissionError) as caught:
        asyncio.run(StrategyService(client).generate(prompt))
    assert caught.value.failure.reason_code == 'CONTRADICTORY'
    client.generate_code.assert_not_awaited()


def test_close_based_highest_since_entry_stop_is_not_rewritten_as_intrabar_high_stop():
    prompt = 'RSI14 30 altında al; RSI14 70 üstündeyse veya girişten itibaren en yüksek günlük kapanışın %5 altında kapanışta kapat.'
    item = accepted(prompt)
    item['trailing_stop'] = dict(percent=5, evidence='%5')
    client = provider(item)
    with pytest.raises(StrategyAdmissionError) as caught:
        asyncio.run(StrategyService(client).generate(prompt))
    assert caught.value.failure.reason_code == 'UNSUPPORTED'
    client.generate_code.assert_not_awaited()
