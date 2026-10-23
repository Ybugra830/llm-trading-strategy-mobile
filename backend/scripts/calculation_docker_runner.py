"""Trusted audit instrumentation, executed ONLY inside the existing sandbox image.

The production worker, strategy loader, broker, metrics and limits stay in use.
No writes/mounts/network are added. stdout carries a second bounded JSON record.
"""

import hashlib
import importlib.metadata
import json
import math
import platform
import sys
from pathlib import Path

sys.path.insert(0, '/sandbox')
import worker
from backtesting import Backtest
from backtesting.backtesting import _Broker
from backtesting._util import _Indicator

audit = dict(signals=[], events=[], state=[], indicators={}, trades=[], equity=[])
original_load = worker.load_strategy
original_open, original_close = _Broker._open_trade, _Broker._close_trade


def safe_number(value):
    number = float(value)
    return number if math.isfinite(number) else None


def observed_load(path):
    cls = original_load(path)
    original_next = cls.next

    def observed_next(self):
        old_orders = list(self.orders)
        original_next(self)
        bar = len(self.data) - 1
        for order in self.orders:
            if order not in old_orders:
                audit['signals'].append(dict(bar=bar, action='CLOSE' if order.parent_trade else 'BUY',
                                             size=float(order.size)))
        units = sum(t.size for t in self.trades)
        value = units * float(self.data.Close[-1])
        audit['state'].append(dict(bar=bar, quantity=units, market_value=value,
                                   cash=float(self.equity) - value, equity=float(self.equity)))
    cls.next = observed_next
    return cls


def observed_open(self, price, size, sl, tp, time_index, tag):
    original_open(self, price, size, sl, tp, time_index, tag)
    audit['events'].append(dict(bar=int(time_index), action='BUY', quantity=int(size), price=float(price),
                                commission=float(self._commission(size, price))))


def observed_close(self, trade, price, time_index):
    audit['events'].append(dict(bar=int(time_index), action='CLOSE', quantity=int(trade.size), price=float(price),
                                commission=float(self._commission(trade.size, price))))
    return original_close(self, trade, price, time_index)


class ObservedBacktest(Backtest):
    def run(self, **kwargs):
        stats = super().run(**kwargs)
        audit['equity'] = [safe_number(v) for v in stats['_equity_curve']['Equity']]
        fields = ('Size', 'EntryBar', 'ExitBar', 'EntryPrice', 'ExitPrice', 'Commission', 'PnL')
        audit['trades'] = [{name: safe_number(row[name]) for name in fields}
                           for _, row in stats['_trades'].iterrows()]
        for name, value in vars(stats['_strategy']).items():
            if isinstance(value, _Indicator) and value.ndim == 1:
                audit['indicators'][name] = [safe_number(v) for v in value]
        audit['open_units'] = sum(t.size for t in stats['_strategy'].trades)
        return stats


worker.load_strategy = observed_load
worker.Backtest = ObservedBacktest
_Broker._open_trade, _Broker._close_trade = observed_open, observed_close
worker.main()
audit['worker_sha256'] = hashlib.sha256(Path('/sandbox/worker.py').read_bytes()).hexdigest()
audit['versions'] = {name: importlib.metadata.version(name) for name in ('backtesting', 'ta', 'pandas', 'numpy')}
audit['versions']['python'] = platform.python_version()
print(json.dumps({'calculation_audit': audit}, allow_nan=False, separators=(',', ':')))
