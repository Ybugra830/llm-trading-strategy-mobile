"""Synthetic numeric edge cases matching the observed TUPRS cleaner failure."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
import numpy as np
import pandas as pd
import pytest
from app.market.ohlcv_cleaner import clean_ohlcv
from app.market.errors import InvalidMarketDataError

def frame(low):
    return pd.DataFrame({'Open':[100.5], 'High':[101.0], 'Low':[low], 'Close':[100.0], 'Volume':[1000]}, index=pd.to_datetime(['2026-01-05']))

def test_machine_precision_adjustment_noise_does_not_reject_entire_dataset():
    assert len(clean_ohlcv(frame(np.nextafter(100.0, np.inf)))) == 1

def test_materially_invalid_ohlc_stays_rejected():
    with pytest.raises(InvalidMarketDataError):
        clean_ohlcv(frame(100.25))
