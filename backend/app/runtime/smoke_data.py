"""Sandbox teknik smoke testi için deterministik OHLCV."""

import numpy as np
import pandas as pd


def build_smoke_ohlcv() -> pd.DataFrame:
    """Desteklenen standart indikatörler için yeterli 320 bar üret."""
    index = pd.bdate_range("2024-01-02", periods=320, name="Date")
    step = np.arange(len(index), dtype=float)
    close = 100 + (step * 0.025) + (4 * np.sin(step / 11))
    open_price = close + (0.2 * np.cos(step / 7))
    return pd.DataFrame(
        {
            "Open": open_price,
            "High": np.maximum(open_price, close) + 1,
            "Low": np.minimum(open_price, close) - 1,
            "Close": close,
            "Volume": 10_000 + ((step % 50) * 20),
        },
        index=index,
    )
