"""Opt-in real sandbox regression; generated/test source never runs on host."""

import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import get_settings
from scripts.verify_calculations import AuditExecutor, dataframe, read_data
from sandbox.worker import guard_terminal_entries
from backtesting import Strategy
from app.backtest.engine import run_backtest
from scripts.verify_calculations import synthetic_data


def test_trusted_engine_also_cancels_terminal_entry():
    # This repository-owned test class is trusted; no generated source is loaded.
    class LastBarBuyer(Strategy):
        def init(self):
            pass

        def next(self):
            if len(self.data) == 20:
                self.buy()

    stats = run_backtest(dataframe(synthetic_data()), LastBarBuyer, initial_cash=1000, commission=.002)
    assert len(stats['_strategy'].trades) == 0
    assert stats['Equity Final [$]'] == 1000


@pytest.mark.parametrize('current_bars', [19, 20])
def test_guard_cancels_only_terminal_entries_and_preserves_exits(current_bars):
    class Order:
        def __init__(self, parent):
            self.parent_trade = parent
            self.cancelled = False

        def cancel(self):
            self.cancelled = True

    entry, exit_order, stop_order = Order(None), Order(object()), Order(object())

    class TrustedTestStrategy:
        called = False

        def next(self):
            self.called = True

    guard_terminal_entries(TrustedTestStrategy, 20)
    strategy = TrustedTestStrategy()
    strategy.data = [0] * current_bars
    strategy.orders = [entry, exit_order, stop_order]
    strategy.next()
    assert strategy.called
    assert entry.cancelled is (current_bars == 20)
    assert not exit_order.cancelled and not stop_order.cancelled


@pytest.mark.skipif(os.environ.get('RUN_CALCULATION_DOCKER_TESTS') != '1', reason='Explicit real Docker opt-in')
def test_terminal_buy_cannot_open_without_a_future_bar():
    folder = Path(__file__).parent / 'fixtures' / 'terminal_pending_buy'
    code = (folder / 'strategy.py').read_text(encoding='utf-8')
    executor = AuditExecutor(get_settings())
    result = executor.run_backtest(code, hashlib.sha256(code.encode()).hexdigest(),
                                    dataframe(read_data(folder / 'data.csv')), 1000, .002)
    assert result.success
    assert executor.audit['signals'][-1]['bar'] == 19
    assert executor.audit['open_units'] == 0, 'Last-close buy has no next bar and must not be filled at the past Open'
    assert executor.audit['events'] == []
    assert result.metrics.final_equity == 1000
