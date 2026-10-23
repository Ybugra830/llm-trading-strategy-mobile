"""Reproducible real-Docker audit; --capture-rsi opts into one new NVIDIA/Yahoo run.

Default reruns saved CSV/code, never requests fresh model output or market data.
Untrusted strategy source is only loaded inside the existing restricted image.
"""

import argparse
import asyncio
import csv
import hashlib
import json
import logging
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd

from app.config import get_settings
from app.llm.nvidia_client import NvidiaNimClient, NvidiaNimError
from app.llm.prompt_examples import CANONICAL_STRATEGY_EXAMPLES
from app.market.ohlcv_cleaner import clean_ohlcv
from app.market.data_split import split_market_data
from app.market.yahoo_provider import YahooFinanceProvider
from app.runtime.docker_executor import DockerSandboxExecutor
from app.schemas.strategy_lab import StrategyLabRunRequest
from app.services.admission_service import StrategyAdmissionError
from app.services.strategy_lab_service import StrategyLabService
from app.services.strategy_service import StrategyService
from app.services.validation_service import ValidationService
from scripts.calculation_reference import simulate, MONEY_TOLERANCE, INDICATOR_TOLERANCE, METRIC_TOLERANCE

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'verification' / 'calculation'
PROMPT = "14 periyotluk RSI 30'un altındayken pozisyon yoksa al; RSI 70'in üzerindeyken açık pozisyonu kapat."
SMA_CODE = '''from backtesting import Strategy
import pandas as pd
from ta.trend import SMAIndicator

def average(values, window):
    return SMAIndicator(pd.Series(values), window=window).sma_indicator().to_numpy()

class GeneratedStrategy(Strategy):
    def init(self):
        self.fast = self.I(average, self.data.Close, 3)
        self.slow = self.I(average, self.data.Close, 5)

    def next(self):
        up = self.fast[-2] <= self.slow[-2] and self.fast[-1] > self.slow[-1]
        down = self.fast[-2] >= self.slow[-2] and self.fast[-1] < self.slow[-1]
        if not self.position and up:
            self.buy()
        elif self.position and down:
            self.position.close()
'''


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')


def save_csv(path, rows):
    if not rows:
        path.write_text('', encoding='utf-8')
        return
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def read_data(path):
    with path.open(encoding='utf-8', newline='') as stream:
        return [{key: value if key == 'Date' else float(value) for key, value in row.items()}
                for row in csv.DictReader(stream)]


def dataframe(rows):
    return pd.DataFrame(rows).set_index(pd.DatetimeIndex([row['Date'] for row in rows], name='Date')).drop(columns='Date')


class AuditExecutor(DockerSandboxExecutor):
    """Same restrictions/timeout/protocol; a trusted observer reads engine results."""
    auditing = False
    audit = None

    def run_backtest(self, code, strategy_code_hash, data, initial_cash, commission):
        self.auditing = True
        self.frozen_code, self.frozen_data = code, data.copy()
        try:
            return super().run_backtest(code, strategy_code_hash, data, initial_cash, commission)
        finally:
            self.auditing = False

    def _build_command(self, input_dir, container_name):
        command = super()._build_command(input_dir, container_name)
        if self.auditing:
            command[-1:-1] = ['--entrypoint=python']
            command.append('/input/calculation_docker_runner.py')
        return command

    def _write_inputs(self, input_dir, *args):
        super()._write_inputs(input_dir, *args)
        if self.auditing:
            path = input_dir / 'calculation_docker_runner.py'
            path.write_bytes(Path(__file__).with_name('calculation_docker_runner.py').read_bytes())
            path.chmod(0o644)

    def _parse_result(self, stdout, stage, strategy_code_hash):
        if not self.auditing:
            return super()._parse_result(stdout, stage, strategy_code_hash)
        lines = stdout.splitlines()
        if len(lines) != 2:
            raise RuntimeError('Audit output does not have two bounded records')
        result = super()._parse_result(lines[0], stage, strategy_code_hash)
        self.audit = json.loads(lines[1])['calculation_audit']
        return result


def synthetic_data():
    prices = [10, 10, 10, 10, 10, 9, 8, 9, 10, 12, 15, 18, 18, 17, 16, 15, 14, 13, 12, 11]
    return [dict(Date=d.date().isoformat(), Open=p + .5, High=p + 1, Low=p - 1, Close=p, Volume=1000)
            for d, p in zip(pd.bdate_range('2026-01-05', periods=len(prices)), prices)]


def comparison(application, reference):
    rows = []
    for key, expected in reference.items():
        actual = application.get(key)
        tolerance = MONEY_TOLERANCE if key in ('final_equity', 'net_profit', 'total_commission') else 0 if key == 'number_of_trades' else METRIC_TOLERANCE
        difference = None if actual is None or expected is None else actual - expected
        passed = actual is None and expected is None or difference is not None and abs(difference) <= tolerance
        rows.append(dict(metric=key, application=actual, independent=expected, difference=difference,
                         tolerance=tolerance, result='PASS' if passed else 'FAIL'))
    return rows


def verify_case(folder, family, settings, *, initial_cash, commission, fixed_signals=None, indicator_values=None):
    code_path, data_path = folder / 'strategy.py', folder / 'data.csv'
    code, data = code_path.read_text(encoding='utf-8'), read_data(data_path)
    validation = ValidationService().prepare(code)
    if not validation.validation.valid:
        raise RuntimeError('Frozen source failed actual validation')
    executor = AuditExecutor(settings)
    result = executor.run_backtest(code, hashlib.sha256(code.encode()).hexdigest(), dataframe(data), initial_cash, commission)
    if not result.success:
        raise RuntimeError('Actual Docker backtest failed')
    audit = executor.audit
    if audit['worker_sha256'] != digest(ROOT / 'sandbox' / 'worker.py'):
        raise RuntimeError('Sandbox image worker does not match source')
    reference = simulate(data, family, initial_cash, commission, fixed_signals=fixed_signals, indicator_values=indicator_values)
    app_metrics = result.metrics.model_dump()
    app_metrics['total_commission'] = sum(e['commission'] for e in audit['events'])
    comparisons = comparison(app_metrics, reference['metrics'])
    equity_difference = max(abs(a - row['equity']) for a, row in zip(audit['equity'], reference['rows']))
    actual_signals = [{k: s[k] for k in ('bar', 'action')} for s in audit['signals']]
    trade_matches = len(audit['trades']) == len(reference['trades']) and all(
        abs(a[key] - b[key]) <= MONEY_TOLERANCE for a, b in zip(audit['trades'], reference['trades']) for key in b)
    expected_indicators = {key: [row[key] for row in reference['rows']] for key in (('fast', 'slow') if family == 'sma' else ('rsi',))}
    indicator_checks = {}
    for name, expected in expected_indicators.items():
        differences = []
        for actual in audit['indicators'].values():
            if len(actual) != len(expected) or any((a is None) != (b is None) for a, b in zip(actual, expected)):
                continue
            differences.append(max((abs(a - b) for a, b in zip(actual, expected) if a is not None), default=0))
        indicator_checks[name] = min(differences) if differences else None
    states = {state['bar']: state for state in audit['state']}
    for i, row in enumerate(reference['rows']):
        row['application_equity'] = audit['equity'][i]
        row['application_signal'] = ';'.join(s['action'] for s in audit['signals'] if s['bar'] == i)
        row['application_executed'] = ';'.join(e['action'] for e in audit['events'] if e['bar'] == i)
        row['application_commission'] = sum(e['commission'] for e in audit['events'] if e['bar'] == i)
        # Conventional cash = total equity - market value; engine _cash is margin accounting.
        units = audit['open_units'] if i == len(data) - 1 else states.get(i, {}).get('quantity', 0)
        row['application_quantity'] = units
        row['application_market_value'] = units * float(data[i]['Close'])
        row['application_cash'] = audit['equity'][i] - row['application_market_value']
    holdings_match = all(row['quantity'] == row['application_quantity'] and
                         abs(row['cash'] - row['application_cash']) <= MONEY_TOLERANCE for row in reference['rows'])
    passed = (all(row['result'] == 'PASS' for row in comparisons) and equity_difference <= MONEY_TOLERANCE
              and actual_signals == reference['signals'] and trade_matches and holdings_match
              and len(audit['equity']) == len(data)
              and all(d is not None and d <= INDICATOR_TOLERANCE for d in indicator_checks.values()))
    save_csv(folder / 'bars.csv', reference['rows'])
    def dated_trades(trades, signals):
        result = []
        for trade in trades:
            entry_bar, exit_bar = int(trade['EntryBar']), int(trade['ExitBar'])
            entry_signal = next((s['bar'] for s in signals if s['action'] == 'BUY' and s['bar'] == entry_bar - 1), None)
            exit_signal = next((s['bar'] for s in signals if s['action'] == 'CLOSE' and s['bar'] == exit_bar - 1), None)
            result.append(dict(**trade, EntryDate=data[entry_bar]['Date'], ExitDate=data[exit_bar]['Date'],
                               EntrySignalBar=entry_signal,
                               ExitSignalBar=exit_signal, ExitReason='next_open' if exit_signal is not None else 'finalize_last_open'))
        return result
    save_csv(folder / 'application_trades.csv', dated_trades(audit['trades'], actual_signals))
    save_csv(folder / 'independent_trades.csv', dated_trades(reference['trades'], reference['signals']))
    save_csv(folder / 'application_events.csv', audit['events'])
    save_csv(folder / 'independent_events.csv', reference['events'])
    save_csv(folder / 'metrics.csv', comparisons)
    save_json(folder / 'application_audit.json', audit)
    report = dict(passed=passed, initial_cash=initial_cash, commission=commission,
                  warmup=reference['warmup'], first_next_bar=reference['warmup'] + 1,
                  equity_max_difference=equity_difference, indicator_max_differences=indicator_checks,
                  signals_match=actual_signals == reference['signals'], trades_match=trade_matches,
                  holdings_match=holdings_match, metrics=comparisons,
                  code_sha256=digest(code_path), data_sha256=digest(data_path), versions=audit['versions'])
    save_json(folder / 'comparison.json', report)
    save_json(folder / 'audit_manifest.json', dict(verified_at=datetime.now(timezone.utc).isoformat(),
        code_sha256=report['code_sha256'], data_sha256=report['data_sha256'],
        worker_sha256=audit['worker_sha256'], audit_runner_sha256=digest(Path(__file__).with_name('calculation_docker_runner.py')),
        versions=audit['versions'], initial_cash=initial_cash, commission=commission,
        spread=0, margin=1, trade_on_close=False, exclusive_orders=True, finalize_trades=True,
        slippage='not modeled', sandbox_image=settings.sandbox_image,
        image_id=subprocess.check_output(['docker', 'image', 'inspect', settings.sandbox_image, '--format', '{{.Id}}'], text=True).strip()))
    print(json.dumps(dict(case=folder.name, passed=passed, equity_max_difference=equity_difference,
                          indicators=indicator_checks, signals_match=report['signals_match']), ensure_ascii=True), flush=True)
    return report


async def capture_rsi(settings):
    folder = OUTPUT / 'rsi'
    if (folder / 'strategy.py').exists() or (folder / 'data.csv').exists():
        raise RuntimeError('RSI snapshot already exists; it will not be overwritten')
    folder.mkdir(parents=True, exist_ok=True)
    executor = AuditExecutor(settings)
    async with NvidiaNimClient(settings) as client:
        strategy = StrategyService(client)
        service = StrategyLabService(strategy, ValidationService(), executor, YahooFinanceProvider(),
                                     max_strategy_versions=settings.max_strategy_versions)
        response = await service.run(StrategyLabRunRequest(prompt=PROMPT, symbol='THYAO', initial_cash=100000, commission=.002))
        approved = json.loads(strategy._approved[PROMPT].generation_prompt)
    (folder / 'strategy.py').write_bytes(executor.frozen_code.encode('utf-8'))
    executor.frozen_data.to_csv(folder / 'data.csv', index_label='Date', float_format='%.17g')
    save_json(folder / 'approved_interpretation.json', approved)
    save_json(folder / 'captured_response.json', response.model_dump(mode='json'))
    save_json(folder / 'capture_manifest.json', dict(captured_at=datetime.now(timezone.utc).isoformat(),
        prompt=PROMPT, symbol=response.symbol, yahoo_symbol=response.yahoo_symbol,
        model=response.generation.model, attempt_count=response.generation.attempt_count,
        configuration=response.configuration.model_dump(), data=response.data.model_dump(mode='json'),
        versions=executor.audit['versions'], sandbox_image=settings.sandbox_image,
        image_id=subprocess.check_output(['docker', 'image', 'inspect', settings.sandbox_image, '--format', '{{.Id}}'], text=True).strip(),
        code_sha256=digest(folder / 'strategy.py'), data_sha256=digest(folder / 'data.csv'),
        worker_sha256=executor.audit['worker_sha256'], audit_runner_sha256=digest(Path(__file__).with_name('calculation_docker_runner.py')),
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        dirty_working_tree=True, previous_result_reproducible=False,
        backtest=dict(spread=0, margin=1, trade_on_close=False, exclusive_orders=True, finalize_trades=True, slippage='not modeled'),
        history_used_for_indicator_warmup=False))


def capture_reference_rsi(settings):
    """Explicit diagnostic fixture, NEVER an admission or generated-code fallback."""
    folder = OUTPUT / 'rsi'
    if (folder / 'strategy.py').exists() or (folder / 'data.csv').exists():
        raise RuntimeError('RSI snapshot already exists; it will not be overwritten')
    folder.mkdir(exist_ok=True)
    source = next(example.source for example in CANONICAL_STRATEGY_EXAMPLES if example.family == 'RSI')
    source = source.strip().replace('< 35', '< 30') + '\n'
    prepared = ValidationService().prepare(source, PROMPT)
    if not prepared.validation.valid:
        raise RuntimeError('Repository reference failed validation')
    source = prepared.code
    code_hash = hashlib.sha256(source.encode()).hexdigest()
    executor = AuditExecutor(settings)
    if not executor.run_smoke(source, code_hash, 100000, .002).success:
        raise RuntimeError('Repository reference failed Docker smoke')
    clean = clean_ohlcv(YahooFinanceProvider().download_daily('THYAO.IS'))
    split = split_market_data(clean)
    (folder / 'strategy.py').write_bytes(source.encode('utf-8'))
    clean.to_csv(folder / 'downloaded_clean_history.csv', index_label='Date', float_format='%.17g')
    split.test_data.to_csv(folder / 'data.csv', index_label='Date', float_format='%.17g')
    save_json(folder / 'intended_rules.json', dict(prompt=PROMPT, source='explicit human rule; not a model admission',
              entry='not position and RSI14 < 30', exit='position and RSI14 > 70', size='default full available equity; whole units'))
    save_json(folder / 'capture_manifest.json', dict(captured_at=datetime.now(timezone.utc).isoformat(),
        source_kind='repository_reference_NOT_NVIDIA_generated', admission_verified=False,
        reason='Two real admission attempts failed: invalid indicator reference, then timeout. No gate bypass in app.',
        model=None, symbol='THYAO', yahoo_symbol='THYAO.IS', prompt=PROMPT,
        initial_cash=100000, commission=.002, test_start=split.test_data.index.min().isoformat(),
        test_end=split.test_data.index.max().isoformat(), test_bars=len(split.test_data), history_bars=len(split.history_data),
        cutoff=split.cutoff_date.isoformat(), code_sha256=digest(folder / 'strategy.py'), data_sha256=digest(folder / 'data.csv'),
        history_sha256=digest(folder / 'downloaded_clean_history.csv'), sandbox_image=settings.sandbox_image,
        image_id=subprocess.check_output(['docker', 'image', 'inspect', settings.sandbox_image, '--format', '{{.Id}}'], text=True).strip(),
        commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), dirty_working_tree=True,
        history_used_for_indicator_warmup=False, previous_result_reproducible=False,
        backtest=dict(spread=0, margin=1, trade_on_close=False, exclusive_orders=True, finalize_trades=True, slippage='not modeled')))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    capture = parser.add_mutually_exclusive_group()
    capture.add_argument('--capture-rsi', action='store_true')
    capture.add_argument('--capture-reference-rsi', action='store_true', help='Explicit trusted repository fixture, not NVIDIA generation')
    args = parser.parse_args()
    for name in ('httpx', 'httpcore', 'openai'):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    settings = get_settings()
    OUTPUT.mkdir(parents=True, exist_ok=True)
    # Tolerances are fixed in source BEFORE any comparisons, not tuned to results.
    save_json(OUTPUT / 'tolerances.json', dict(money_absolute=MONEY_TOLERANCE, indicator_absolute=INDICATOR_TOLERANCE,
              metric_absolute=METRIC_TOLERANCE, counts_bars_signals='exact', rationale='float64 arithmetic/CSV roundtrip; below 0.0001 currency unit'))
    if args.capture_rsi:
        try:
            asyncio.run(capture_rsi(settings))
        except (NvidiaNimError, StrategyAdmissionError) as error:
            save_json(OUTPUT / 'capture_failure.json', dict(error_type=type(error).__name__, provider_kind=getattr(error, 'kind', None)))
            print('Real RSI capture failed safely; see capture_failure.json. No fabricated replacement.')
    if args.capture_reference_rsi:
        capture_reference_rsi(settings)
    reports = []
    for name, commission in [('sma_zero', 0), ('sma_commission', .002)]:
        folder = OUTPUT / name
        folder.mkdir(exist_ok=True)
        save_csv(folder / 'data.csv', synthetic_data())
        (folder / 'strategy.py').write_bytes(SMA_CODE.encode('utf-8'))
        reports.append(verify_case(folder, 'sma', settings, initial_cash=1000, commission=commission))
    rsi_folder = OUTPUT / 'rsi'
    if (rsi_folder / 'strategy.py').exists() and (rsi_folder / 'data.csv').exists():
        manifest = json.loads((rsi_folder / 'capture_manifest.json').read_text(encoding='utf-8'))
        if digest(rsi_folder / 'strategy.py') != manifest['code_sha256'] or digest(rsi_folder / 'data.csv') != manifest['data_sha256']:
            raise RuntimeError('Frozen RSI code/data hash mismatch')
        reports.append(verify_case(rsi_folder, 'rsi', settings, initial_cash=100000, commission=.002))
    else:
        print('RSI snapshot missing; --capture-rsi explicitly opts into real NVIDIA/Yahoo.')
    source_kind = (json.loads((rsi_folder / 'capture_manifest.json').read_text(encoding='utf-8')).get('source_kind', 'NVIDIA_generated')
                   if (rsi_folder / 'capture_manifest.json').exists() else 'missing')
    summary = dict(numerical_verification_passed=len(reports) == 3 and all(r['passed'] for r in reports),
                   nvidia_generation_verified=source_kind == 'NVIDIA_generated',
                   rsi_source_kind=source_kind, verified_cases=len(reports))
    save_json(OUTPUT / 'summary.json', dict(**summary, reports=reports))
    print(json.dumps(summary), flush=True)
    return 0 if len(reports) == 3 and all(r['passed'] for r in reports) else 1


if __name__ == '__main__':
    raise SystemExit(main())
