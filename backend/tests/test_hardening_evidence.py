"""Benchmark counters distinguish retries, provider failures, and output failures."""
import logging

from scripts.run_hardening_acceptance import Evidence, summarize
from scripts.hardening_cases import PRODUCTION_MODEL


def event(name, template, *args):
    return logging.LogRecord(name, logging.INFO, '', 0, template, args, None)


def test_attempt_metrics_do_not_store_provider_or_header_text():
    evidence = Evidence()
    evidence.emit(event('app.llm.nvidia_client', 'NVIDIA NIM attempt started model=%s attempt=%s', PRODUCTION_MODEL, 1))
    evidence.emit(event('httpx', 'HTTP Request: POST https://integrate.api.nvidia.com/v1/chat/completions "HTTP/1.1 503 Service Unavailable" secret=nvapi-must-not-persist'))
    evidence.emit(event('app.llm.nvidia_client', 'NVIDIA NIM request failed model=%s attempt=%s duration_seconds=%.3f %s', PRODUCTION_MODEL, 1, 20., 'category=provider_5xx status=503 message=safe'))
    evidence.emit(event('app.llm.nvidia_client', 'NVIDIA NIM attempt started model=%s attempt=%s', PRODUCTION_MODEL, 2))
    evidence.emit(event('app.llm.nvidia_client', 'NVIDIA NIM request failed model=%s category=%s duration_seconds=%.3f', PRODUCTION_MODEL, 'provider_timeout', 180.))
    calls = evidence.sanitized()
    assert len(calls) == 2 and calls[0]['http_status'] == 503
    assert calls[0]['category'] == 'provider_5xx'
    assert calls[1]['attempt'] == 2 and calls[1]['category'] == 'provider_timeout'
    assert 'nvapi' not in str(calls) and 'started' not in calls[0]
    row = dict(model=PRODUCTION_MODEL, provider_attempts=calls, passed=False, http_status=502,
               first_static=None, first_smoke=None, attempts=[], repairs=0, generation_seconds=180.,
               duration_seconds=180.5, within_flutter_budget=True)
    totals = summarize([row])[0]
    assert totals['code_received'] == 0 and totals['first_static'] == 0
    assert totals['count_503'] == 1 and totals['timeouts'] == 1 and totals['provider_retries'] == 1


def test_installed_backtesting_api_contract():
    import backtesting
    from backtesting.backtesting import Position, Trade
    assert backtesting.__version__ == '0.6.6'
    assert not hasattr(Position, 'entry_price')
    assert callable(Position.close) and callable(Position.__bool__)
    assert isinstance(Trade.entry_price, property) and Trade.entry_price.fset is None
    assert isinstance(Trade.sl, property) and Trade.sl.fset is not None
