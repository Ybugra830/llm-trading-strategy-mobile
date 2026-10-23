"""One shared source for documented indicator defaults and supported outputs."""

INDICATOR_DEFAULTS = {
    "rsi": {"window": 14},
    "sma": {"window": 20},
    "ema": {"window": 10},
    "macd": {"window_fast": 12, "window_slow": 26, "window_signal": 9},
    "bollinger": {"window": 20, "deviation": 2},
    "stochastic": {"window": 14, "smooth_window": 3},
    "atr": {"window": 14},
}
PAIR_WINDOWS = {"sma": {"fast": 20, "slow": 50}, "ema": {"fast": 10, "slow": 30}}
INDICATOR_OUTPUTS = {
    "rsi": {"value"}, "sma": {"value"}, "ema": {"value"}, "atr": {"value"},
    "macd": {"line", "signal", "histogram"},
    "bollinger": {"lower", "middle", "upper"}, "stochastic": {"k", "d"},
}
