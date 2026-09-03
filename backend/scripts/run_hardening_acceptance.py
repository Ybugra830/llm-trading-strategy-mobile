"""Real route acceptance and 30-request model comparison; no persistent config writes."""
import argparse
import asyncio
from contextlib import aclosing
from datetime import UTC, date, datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import re
import statistics
import subprocess
import sys
from time import perf_counter

import httpx

from app.api.strategy_lab_routes import get_strategy_lab_service
from app.config import get_settings
from app.llm.nvidia_options import get_model_options
from app.llm.prompt_builder import build_strategy_messages
from app.main import app
from scripts.hardening_cases import CASES, PRODUCTION_MODEL, COMPARISON_MODEL
from scripts.run_strategy_reliability_matrix import ReliabilityObserver


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


class Evidence(logging.Handler):
    """Capture only enumerated metrics, never rendered SDK/provider log contents."""
    def __init__(self):
        super().__init__()
        self.provider = []
        self.budget_expirations = []

    def emit(self, record):
        args = record.args
        template = str(record.msg)
        if record.name == 'httpx':
            text = record.getMessage()
            if '/chat/completions' in text and self.provider:
                match = re.search(r'HTTP/\S+ (\d{3})', text)
                if match:
                    self.provider[-1]['http_status'] = int(match.group(1))
        elif record.name == 'app.llm.nvidia_client':
            if template.startswith('NVIDIA NIM attempt started'):
                self.provider.append(dict(model=args[0], attempt=args[1], http_status=None, category=None,
                                          started=perf_counter(), duration_seconds=None, returned_code=False))
            elif template.startswith('NVIDIA NIM request succeeded') and self.provider:
                self.provider[-1].update(duration_seconds=round(args[3], 3), returned_code=True)
            elif template.startswith('NVIDIA NIM empty response') and self.provider:
                self.provider[-1].update(duration_seconds=round(args[2], 3), category='invalid_response')
            elif template.startswith('NVIDIA NIM request failed'):
                if 'attempt=%s' in template and self.provider:
                    match = re.search(r'category=([a-z0-9_]+)', args[3])
                    self.provider[-1].update(duration_seconds=round(args[2], 3), category=match.group(1) if match else 'unknown')
                elif self.provider:
                    self.budget_expirations.append(dict(category=args[1], duration_seconds=round(args[2], 3)))
                    if self.provider[-1]['duration_seconds'] is None:
                        self.provider[-1].update(duration_seconds=round(perf_counter()-self.provider[-1]['started'], 3), category=args[1])

    def sanitized(self):
        return [{k: v for k, v in item.items() if k != 'started'} for item in self.provider]


class Observer(ReliabilityObserver):
    def __init__(self):
        super().__init__()
        self.provider_started = perf_counter()
        self.durations = []

    def on_generated(self, attempt, source, generated):
        super().on_generated(attempt, source, generated)
        elapsed = round(perf_counter()-self.provider_started, 3)
        self.attempts[-1]['provider_duration_seconds'] = elapsed
        self.durations.append(elapsed)

    def on_repair_requested(self, failed_attempt, next_attempt, context):
        super().on_repair_requested(failed_attempt, next_attempt, context)
        self.repair_requests[-1]['context']['family'] = context.family
        self.provider_started = perf_counter()


def configuration():
    settings = get_settings()
    assert settings.nvidia_model in (PRODUCTION_MODEL, COMPARISON_MODEL)
    assert not settings.nvidia_fallback_model, 'Fallback must remain disabled'
    assert settings.nvidia_max_tokens == 2048 and settings.nvidia_request_timeout_seconds == 180
    assert get_model_options(PRODUCTION_MODEL) == get_model_options(COMPARISON_MODEL)
    return dict(model=settings.nvidia_model, fallback=None, max_tokens=settings.nvidia_max_tokens,
                provider_budget_seconds=settings.nvidia_request_timeout_seconds,
                max_retries=settings.nvidia_max_retries, options=get_model_options(settings.nvidia_model),
                max_strategy_versions=settings.max_strategy_versions, sandbox_image=settings.sandbox_image)


async def child(case, as_of, output):
    config = configuration()
    started_at = datetime.now(UTC).isoformat()
    started = perf_counter()
    evidence, observer = Evidence(), Observer()
    for name in ('app.llm.nvidia_client', 'httpx'):
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.addHandler(evidence)
        logger.propagate = False
    yahoo = dict(reached=False, success=False)
    async def observed_service():
        # Production dependency and pipeline; only attach observers and fix the
        # existing Yahoo date seam so every model sees the same date interval.
        async with aclosing(get_strategy_lab_service()) as services:
            async for service in services:
                service._observer = observer
                provider = service._market_provider
                provider._today_provider = lambda: as_of
                download = provider.download_daily
                def observed_download(symbol):
                    yahoo.update(reached=True, symbol=symbol)
                    begin = perf_counter()
                    try:
                        frame = download(symbol)
                        yahoo.update(success=True, rows=len(frame),
                                     start=str(frame.index.min()), end=str(frame.index.max()),
                                     data_sha256=hashlib.sha256(frame.to_csv().encode()).hexdigest())
                        return frame
                    finally:
                        yahoo['duration_seconds'] = round(perf_counter()-begin, 3)
                provider.download_daily = observed_download
                yield service
    app.dependency_overrides[get_strategy_lab_service] = observed_service
    body, status, error_type = {}, None, None
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://strategy-lab.local') as client:
            # Observe overruns rather than silently changing the existing policy.
            async with asyncio.timeout(750):
                response = await client.post('/api/v1/strategy-lab/run', json=dict(
                    prompt=case.prompt, symbol='AKBNK', initial_cash=case.cash, commission=.0005))
            status, body = response.status_code, response.json()
    except Exception as error:
        error_type = type(error).__name__
    finally:
        app.dependency_overrides.pop(get_strategy_lab_service, None)
        for name in ('app.llm.nvidia_client', 'httpx'):
            logging.getLogger(name).removeHandler(evidence)
    elapsed = round(perf_counter()-started, 3)
    if not observer.attempts or (observer.repair_requests and len(observer.attempts) <= len(observer.repair_requests)):
        observer.durations.append(round(perf_counter()-observer.provider_started, 3))
    runtime = body.get('runtime', {})
    attempts = observer.attempts
    first = attempts[0] if attempts else {}
    record = dict(case=case.name, prompt=case.prompt, model=config['model'], config=config,
                  as_of=as_of.isoformat(), started_at=started_at, completed_at=datetime.now(UTC).isoformat(), symbol='AKBNK',
                  cash=case.cash, commission=.0005, duration_seconds=elapsed,
                  generation_seconds=round(sum(observer.durations), 3), http_status=status,
                  response_status=body.get('status'), error_type=error_type, safe_detail=body.get('detail'),
                  first_static=(first.get('validation') or {}).get('valid'),
                  first_smoke=(first.get('smoke') or {}).get('success'),
                  repairs=len(observer.repair_requests), attempts=attempts, repair_requests=observer.repair_requests,
                  provider_attempts=evidence.sanitized(), budget_expirations=evidence.budget_expirations,
                  yahoo=yahoo, backtest=observer.backtest, runtime=runtime,
                  final_validation=body.get('validation'), data=body.get('data'), within_flutter_budget=elapsed<=300,
                  prompt_sha256=hashlib.sha256(json.dumps(build_strategy_messages(case.prompt), sort_keys=True).encode()).hexdigest())
    record['passed'] = bool(status == 200 and body.get('status') == 'success' and
                            (body.get('validation') or {}).get('valid') and runtime.get('sandboxed') is True
                            and runtime.get('smoke_test_passed') is True and yahoo['success'] and
                            observer.backtest and observer.backtest['success'] and elapsed <= 300)
    write(output, record)
    print(json.dumps({k: record[k] for k in ('case','model','http_status','duration_seconds','generation_seconds','first_static','first_smoke','repairs','passed')}), flush=True)
    return 0  # Failed runs remain evidence; parent must still run every scheduled case.


async def availability(output):
    settings = get_settings()
    record = dict(checked_at=datetime.now(UTC).isoformat(), http_status=None, models={})
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(settings.nvidia_base_url.rstrip('/') + '/models',
                headers={'Authorization': 'Bearer ' + settings.nvidia_api_key.get_secret_value()})
            record['http_status'] = response.status_code
            ids = {item['id'] for item in response.json().get('data', [])} if response.is_success else set()
            record['models'] = {name: name in ids for name in (PRODUCTION_MODEL, COMPARISON_MODEL)}
    except Exception as error:
        record['error_type'] = type(error).__name__
    write(output, record)
    print(json.dumps({'availability': record}), flush=True)


def summarize(records):
    rows = []
    for model in (PRODUCTION_MODEL, COMPARISON_MODEL):
        selected = [r for r in records if r['model'] == model]
        if not selected:
            continue
        calls = [call for r in selected for call in r['provider_attempts']]
        rows.append(dict(model=model, requests=len(selected), http_200=sum(r['http_status']==200 for r in selected),
            accepted=sum(r['passed'] for r in selected), first_static=sum(r['first_static'] is True for r in selected),
            first_smoke=sum(r['first_smoke'] is True for r in selected),
            code_received=sum(bool(r['attempts']) for r in selected),
            provider_http_statuses={str(s): sum(c['http_status']==s for c in calls) for s in {c['http_status'] for c in calls}},
            count_503=sum(c['http_status']==503 for c in calls), timeouts=sum(c['category']=='provider_timeout' for c in calls),
            provider_retries=sum(c['attempt']>1 for c in calls), repairs=sum(r['repairs'] for r in selected),
            generation_total_seconds=round(sum(r['generation_seconds'] for r in selected), 3),
            generation_median_seconds=round(statistics.median(r['generation_seconds'] for r in selected), 3),
            mean_request_seconds=round(statistics.mean(r['duration_seconds'] for r in selected), 3),
            over_300_seconds=sum(not r['within_flutter_budget'] for r in selected)))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['initial','benchmark','final','child'], required=True)
    parser.add_argument('--case', choices=[c.name for c in CASES])
    parser.add_argument('--as-of', type=date.fromisoformat, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'child':
        logging.getLogger().addHandler(logging.NullHandler())
        return asyncio.run(child(next(c for c in CASES if c.name == args.case), args.as_of, args.output))
    assert get_settings().nvidia_model == PRODUCTION_MODEL, 'Persistent production model changed'
    configuration()
    args.output.mkdir(parents=True, exist_ok=True)
    tracked = ['app/llm/nvidia_client.py', 'app/llm/prompt_builder.py', 'app/llm/prompt_examples.py',
               'app/validators/strategy_contract.py', 'app/llm/repair_context.py', 'sandbox/worker.py']
    write(args.output / 'manifest.json', dict(config=configuration(), source_sha256={
        path: hashlib.sha256(Path(path).read_bytes()).hexdigest() for path in tracked}))
    records = []
    if args.mode == 'benchmark':
        asyncio.run(availability(args.output / 'availability.json'))
    for round_number in range(1, 6 if args.mode == 'benchmark' else 2):
        models = [PRODUCTION_MODEL, COMPARISON_MODEL] if args.mode == 'benchmark' else [PRODUCTION_MODEL]
        if round_number % 2 == 0:
            models.reverse()
        for case in CASES:
            for model in models:
                env = os.environ.copy()
                env['NVIDIA_MODEL'] = model  # Only a child-process override; never touch .env.
                short = 'super' if model == PRODUCTION_MODEL else 'mistral'
                output = args.output / f'{round_number}-{case.name}-{short}.json'
                print(json.dumps(dict(event='started', round=round_number, case=case.name, model=model)), flush=True)
                result = subprocess.run([sys.executable, '-B', '-m', 'scripts.run_hardening_acceptance',
                    '--mode', 'child', '--case', case.name, '--as-of', args.as_of.isoformat(), '--output', str(output.resolve())], env=env)
                if result.returncode != 0 or not output.exists():
                    raise RuntimeError('Acceptance runner infrastructure failure; preserve prior evidence')
                records.append(json.loads(output.read_text(encoding='utf-8')))
                write(args.output / 'summary.json', dict(runs=records, models=summarize(records)))
    print(json.dumps({'models': summarize(records)}), flush=True)
    return 0 if args.mode == 'benchmark' or all(r['passed'] for r in records) else 1


if __name__ == '__main__':
    raise SystemExit(main())
