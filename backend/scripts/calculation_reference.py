"""Trusted independent oracle: standard library only, no engine/ta/app metrics."""

import math
import statistics
from datetime import date

MONEY_TOLERANCE = 1e-6
INDICATOR_TOLERANCE = 1e-9
METRIC_TOLERANCE = 1e-8
FULL_SIZE = 1 - 2 ** -52  # Strategy._FULL_EQUITY, not the rounded repr '.9999'.


def sma(prices, window):
    return [None if i + 1 < window else sum(prices[i + 1 - window:i + 1]) / window
            for i in range(len(prices))]


def rsi(prices, window=14):
    """ta 0.11 definition: zero seed at index 0; recursive EWM, not SMA seed."""
    gain = loss = 0.0
    result = []
    for i, price in enumerate(prices):
        change = price - prices[i - 1] if i else 0.0
        gain = (1 - 1 / window) * gain + max(change, 0) / window
        loss = (1 - 1 / window) * loss + max(-change, 0) / window
        result.append(None if i < window - 1 else 100.0 if loss == 0 else 100 - 100 / (1 + gain / loss))
    return result


def simulate(data, family, initial_cash, commission, *, finalize=True, fixed_signals=None, indicator_values=None):
    prices = [float(row['Close']) for row in data]
    indicators = {'fast': sma(prices, 3), 'slow': sma(prices, 5)} if family == 'sma' else {'rsi': rsi(prices)}
    if indicator_values is not None:
        indicators = indicator_values
    warmup = max(next((i for i, v in enumerate(values) if v is not None), 0) for values in indicators.values())
    start = warmup + 1
    cash, units, entry = float(initial_cash), 0, None
    pending = None
    trades, events, rows, signals = [], [], [], []

    def execute(action, i, reason):
        nonlocal cash, units, entry
        price = float(data[i]['Open'])
        if action == 'BUY' and not units:
            quantity = int((cash * FULL_SIZE) // (price * (1 + commission)))
            if not quantity:
                events.append(dict(bar=i, action='CANCEL', quantity=0, price=price, commission=0, reason=reason))
                return
            fee = quantity * price * commission
            cash -= quantity * price + fee
            units = quantity
            entry = dict(bar=i, price=price, quantity=quantity, commission=fee)
            events.append(dict(bar=i, action='BUY', quantity=quantity, price=price, commission=fee, reason=reason))
        elif action == 'CLOSE' and units:
            fee = units * price * commission
            cash += units * price - fee
            trades.append(dict(EntryBar=entry['bar'], ExitBar=i, Size=units, EntryPrice=entry['price'],
                               ExitPrice=price, Commission=entry['commission'] + fee,
                               PnL=units * (price - entry['price']) - entry['commission'] - fee))
            events.append(dict(bar=i, action='CLOSE', quantity=units, price=price, commission=fee, reason=reason))
            units, entry = 0, None

    for i, row in enumerate(data):
        if i >= start:
            if pending:
                execute(pending, i, 'next_open')
            pending = None
            if fixed_signals is not None:
                signal = fixed_signals.get(i)
            elif family == 'sma':
                f, s = indicators['fast'], indicators['slow']
                signal = ('BUY' if not units and f[i - 1] <= s[i - 1] and f[i] > s[i]
                          else 'CLOSE' if units and f[i - 1] >= s[i - 1] and f[i] < s[i] else None)
            else:
                value = indicators['rsi'][i]
                signal = 'BUY' if not units and value < 30 else 'CLOSE' if units and value > 70 else None
            if signal:
                signals.append(dict(bar=i, action=signal))
                pending = signal
        else:
            signal = None
        if i == len(data) - 1 and finalize and start < len(data):
            # Worker cancels terminal entries: no next bar exists for a new BUY.
            # Engine still finalizes existing positions at the last Open.
            execute('CLOSE', i, 'finalize_last_open')
        market_value = units * prices[i]
        bar_events = [event for event in events if event['bar'] == i]
        rows.append(dict(bar=i, Date=row['Date'], Open=float(row['Open']), Close=prices[i],
                         **{key: values[i] for key, values in indicators.items()},
                         signal=signal or '', executed=';'.join(e['action'] for e in bar_events),
                         executed_quantity=';'.join(str(e['quantity']) for e in bar_events),
                         quantity=units, commission=sum(e['commission'] for e in bar_events),
                         cash=cash, market_value=market_value, equity=cash + market_value))
    return dict(rows=rows, trades=trades, events=events, signals=signals, warmup=warmup,
                metrics=metrics(rows, trades, events, prices, warmup, initial_cash))


def metrics(rows, trades, events, prices, warmup, initial_cash):
    equity = [row['equity'] for row in rows]
    peak, drawdown = equity[0], 0.0
    for value in equity:
        peak = max(peak, value)
        drawdown = min(drawdown, (value / peak - 1) * 100)
    daily = [equity[i] / equity[i - 1] - 1 for i in range(1, len(equity))]
    weekend_fraction = sum(date.fromisoformat(row['Date'][:10]).weekday() >= 5 for row in rows) / len(rows)
    annual_days = 365 if weekend_fraction > 2 / 7 * .6 else 252
    sharpe = None
    if len(daily) >= 2 and all(value > -1 for value in daily):
        geometric = math.exp(math.fsum(math.log1p(v) for v in daily) / len(daily)) - 1
        variance = statistics.variance(daily)
        annual_return = (1 + geometric) ** annual_days - 1
        annual_variance = (variance + (1 + geometric) ** 2) ** annual_days - (1 + geometric) ** (2 * annual_days)
        volatility = math.sqrt(max(0, annual_variance))
        sharpe = annual_return / volatility if volatility else None
    final = equity[-1]
    return dict(final_equity=final, net_profit=final - initial_cash,
                return_percent=(final / initial_cash - 1) * 100,
                total_commission=sum(event['commission'] for event in events), number_of_trades=len(trades),
                win_rate_percent=100 * sum(t['PnL'] > 0 for t in trades) / len(trades) if trades else None,
                max_drawdown_percent=drawdown, buy_and_hold_return_percent=(prices[-1] / prices[warmup] - 1) * 100,
                sharpe_ratio=sharpe)
