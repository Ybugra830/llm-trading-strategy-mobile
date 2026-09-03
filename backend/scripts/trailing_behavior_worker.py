"""Trusted assertion harness, executed ONLY inside the isolated Docker container."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import backtesting
import numpy as np
import pandas as pd
from backtesting import Backtest


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path('/input') / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def data_for(closes):
    closes = np.asarray(closes, dtype=float)
    opens = np.r_[closes[0], closes[:-1]]
    return pd.DataFrame(dict(Open=opens, Close=closes, High=np.maximum(opens, closes) + .2,
                             Low=np.minimum(opens, closes) - .2, Volume=100000),
                        index=pd.date_range('2024-01-01', periods=len(closes)))


def observed_run(source, data, cash=10000):
    original = load(source).GeneratedStrategy
    trace = []
    class Observed(original):
        def next(self):
            bar = len(self.data) - 1
            active = list(self.trades)
            before = [t.sl for t in active]
            rsi = float(self.rsi[-1])
            original.next(self)
            trace.append(dict(bar=bar, rsi=rsi, high=float(self.data.High[-1]),
                              close=float(self.data.Close[-1]), active=[dict(entry_bar=t.entry_bar,
                              entry=t.entry_price, previous=p, stop=t.sl) for t, p in zip(active, before)]))
    with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
        result = Backtest(data, Observed, cash=cash, commission=.0005, exclusive_orders=True,
                          trade_on_close=False, finalize_trades=True).run()
    return result, trace


def main():
    assert backtesting.__version__ == '0.6.6'
    report = {'backtesting_version': backtesting.__version__, 'checks': {},
              'worker_sha256': hashlib.sha256(Path('/sandbox/worker.py').read_bytes()).hexdigest()}
    # Falling warm-up guarantees a genuine RSI entry, followed by a rise, a small
    # pullback above the stop, and finally a gap below it. No mocked indicators.
    prices = list(range(100, 85, -1)) + [86.5, 87.5, 88.5, 89.5, 89.2, 88.8, 80, 80, 80, 80]
    data = data_for(prices)
    result, trace = observed_run('rsi_trailing', data)
    trades = result['_trades']
    assert len(trades) > 0
    first = trades.iloc[0]
    samples = [row for row in trace if any(t['entry_bar'] == first.EntryBar for t in row['active'])]
    stops = [row['active'][0]['stop'] for row in samples]
    assert len(stops) >= 4 and all(b >= a for a, b in zip(stops, stops[1:]))
    assert max(stops) > stops[0]
    assert any(b['high'] < a['high'] and b['active'][0]['stop'] == a['active'][0]['stop'] for a, b in zip(samples, samples[1:]))
    assert first.ExitBar == 21 and first.ExitPrice == stops[-1]
    assert next(row for row in trace if row['bar'] == first.EntryBar - 1)['rsi'] < 30
    report['checks']['rising_stop_pullback_and_exit'] = dict(passed=True, samples=samples,
        entry_bar=int(first.EntryBar), exit_bar=int(first.ExitBar), exit_price=float(first.ExitPrice))

    # New high occurs on bar 18. Its newly raised SL is above that bar's close;
    # broker must not retroactively fill it inside bar 18. Next open is a gap.
    prospective = data.copy()
    prospective.iloc[18, prospective.columns.get_loc('High')] = 100
    result, trace = observed_run('rsi_trailing', prospective)
    first = result['_trades'].iloc[0]
    assert first.ExitBar == 19 and first.ExitPrice == prospective.iloc[19].Open
    assert trace[[r['bar'] for r in trace].index(18)]['active'][0]['stop'] == 97
    report['checks']['prospective_update_no_retroactive_fill'] = dict(passed=True, exit_bar=19, exit_price=float(first.ExitPrice))

    # Sustained rise moves actual RSI above 70; close order executes next open.
    rally = data_for(list(range(100, 85, -1)) + list(np.arange(86.5, 121, .5)))
    for source in ('rsi', 'rsi_trailing'):
        result, trace = observed_run(source, rally)
        first = result['_trades'].iloc[0]
        signal = next(row for row in trace if row['bar'] == first.ExitBar - 1)
        assert signal['rsi'] > 70 and first.ExitPrice == rally.iloc[int(first.ExitBar)].Open
        assert signal['active'] and (signal['active'][0]['stop'] is None or rally.iloc[int(first.ExitBar)].Low > signal['active'][0]['stop'])
        report['checks'][source + '_logical_close'] = dict(passed=True, signal_rsi=signal['rsi'], exit_bar=int(first.ExitBar))

    # Verify the real indicator adapters and AND/OR signals against independent
    # pandas/ta calculations, including a prior/current-bar EMA downward cross.
    from ta.momentum import RSIIndicator
    from ta.trend import EMAIndicator
    closes = np.r_[np.linspace(80, 120, 100), np.linspace(120, 108, 14), np.linspace(108, 160, 60), np.linspace(160, 60, 70)]
    frame = data_for(closes)
    module = load('ema_rsi')
    fast = EMAIndicator(frame.Close, window=20).ema_indicator().to_numpy()
    slow = EMAIndicator(frame.Close, window=50).ema_indicator().to_numpy()
    rsi = RSIIndicator(frame.Close, window=14).rsi().to_numpy()
    assert np.allclose(module.ema_array(closes, 20), fast, equal_nan=True)
    assert np.allclose(module.rsi_array(closes, 14), rsi, equal_nan=True)
    result, trace = observed_run('ema_rsi', frame, 100000)
    assert len(result['_trades']) > 0
    for _, trade in result['_trades'].iterrows():
        entry, exit = int(trade.EntryBar)-1, int(trade.ExitBar)-1
        assert fast[entry] > slow[entry] and rsi[entry] < 40
        assert (fast[exit-1] >= slow[exit-1] and fast[exit] < slow[exit]) or rsi[exit] > 70
    assert any(fast[i-1] >= slow[i-1] and fast[i] < slow[i] for i in range(51, len(fast)))
    report['checks']['ema_rsi_adapters_and_signals'] = dict(passed=True, trades=len(result['_trades']))
    report['source_hashes'] = {name: hashlib.sha256((Path('/input') / (name + '.py')).read_bytes()).hexdigest() for name in ('rsi','rsi_trailing','ema_rsi')}
    print(json.dumps(report, allow_nan=False))


if __name__ == '__main__':
    main()
