"""Arithmetic identities for the independent oracle; no generated-code execution."""

import asyncio
import math

import httpx
import pytest

from app.api.strategy_lab_routes import get_strategy_lab_service
from app.main import app
from app.llm.nvidia_client import NvidiaNimError
from scripts.calculation_reference import simulate, rsi
from scripts.verify_calculations import synthetic_data


@pytest.mark.parametrize('commission,final,fees,drawdown', [
    (0, 936, 0, -224 / 1160 * 100),
    (.002, 932.16, 3.84, -(1158.016 - 932.16) / 1158.016 * 100),
])
def test_small_example_matches_written_arithmetic(commission, final, fees, drawdown):
    result = simulate(synthetic_data(), 'sma', 1000, commission)
    assert result['signals'] == [{'bar': 9, 'action': 'BUY'}, {'bar': 15, 'action': 'CLOSE'}]
    trade, = result['trades']
    assert (trade['Size'], trade['EntryBar'], trade['ExitBar']) == (64, 10, 16)
    assert result['metrics']['final_equity'] == pytest.approx(final, abs=1e-10)
    assert result['metrics']['total_commission'] == pytest.approx(fees, abs=1e-10)
    assert result['metrics']['max_drawdown_percent'] == pytest.approx(drawdown, abs=1e-10)


def test_rsi_zero_seed_is_not_simple_average_seed():
    prices = [100, 101] + [101] * 11 + [100]
    # One gain at bar 1 decayed twelve times; one loss at bar 13.
    ratio = (13 / 14) ** 12
    assert rsi(prices)[13] == pytest.approx(100 - 100 / (1 + ratio), abs=1e-12)
    assert rsi(prices)[13] != pytest.approx(50)  # SMA-seeded variant differs.
    assert rsi([100] * 20)[13:] == [100] * 7  # Both gain/loss zero: library chooses 100.
    assert rsi(list(range(120, 100, -1)))[13:] == [0] * 7
    assert all(value is None for value in rsi(prices)[:13])


def test_exact_lot_rounding_and_insufficient_cash():
    data = [dict(row, Open=10, High=11, Low=9, Close=10) for row in synthetic_data()]
    result = simulate(data, 'sma', 1000, 0, fixed_signals={5: 'BUY'})
    assert result['events'][0]['quantity'] == 99  # Near-full equity epsilon, not exactly 100%.
    result = simulate(data, 'sma', 9, .002, fixed_signals={5: 'BUY'})
    assert not result['trades'] and result['metrics']['final_equity'] == 9
    assert result['metrics']['win_rate_percent'] is None


def test_unrealized_profit_affects_equity_but_not_closed_trade_win_rate():
    result = simulate(synthetic_data(), 'sma', 1000, .002, finalize=False, fixed_signals={5: 'BUY'})
    assert result['rows'][-1]['quantity'] > 0
    assert result['metrics']['final_equity'] != 1000
    assert result['metrics']['number_of_trades'] == 0
    assert result['metrics']['win_rate_percent'] is None


def test_backend_receives_custom_cash_and_decimal_commission_without_rescaling():
    received = []

    class Boundary:
        async def run(self, request):
            received.append(request)
            raise NvidiaNimError('Safe test boundary; do not call provider')

    app.dependency_overrides[get_strategy_lab_service] = lambda: Boundary()

    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            return await client.post('/api/v1/strategy-lab/run', json={
                'prompt': 'RSI 30 altında al, 70 üzerinde sat.', 'symbol': 'THYAO',
                'initial_cash': 123456.75, 'commission': .002})

    try:
        response = asyncio.run(send())
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 502  # Intentionally stop after schema/route, not a real provider test.
    assert received[0].initial_cash == 123456.75
    assert received[0].commission == .002
