"""Backend testleri için ortak pytest yapılandırması ve fixture'lar."""

import tempfile
from pathlib import Path
from typing import Final

import numpy as np
import pandas as pd
import pytest

_PYTEST_TEMP_DIRECTORY: Final[pytest.StashKey[tempfile.TemporaryDirectory[str]]] = (
    pytest.StashKey()
)


def pytest_configure(config: pytest.Config) -> None:
    """Her çalıştırma için kullanıcıya ait, çakışmayan bir base temp oluştur."""
    if config.option.basetemp is not None:
        return

    temporary_directory = tempfile.TemporaryDirectory(
        prefix="llm-trading-strategy-pytest-"
    )
    config.stash[_PYTEST_TEMP_DIRECTORY] = temporary_directory
    config.option.basetemp = Path(temporary_directory.name)


def pytest_unconfigure(config: pytest.Config) -> None:
    """Bu pytest çalıştırmasına ait geçici dizini güvenli biçimde temizle."""
    temporary_directory = config.stash.get(_PYTEST_TEMP_DIRECTORY, None)
    if temporary_directory is not None:
        temporary_directory.cleanup()


@pytest.fixture
def ohlcv_data() -> pd.DataFrame:
    """Üç yıldan uzun, kontrollü dalgalanan günlük OHLCV üret."""
    index = pd.bdate_range("2023-01-02", "2026-06-30", name="Date")
    step = np.arange(len(index), dtype=float)
    close = 100 + (step * 0.03) + (5 * np.sin(step / 9))
    open_price = close + (0.3 * np.cos(step / 7))
    return pd.DataFrame(
        {
            "Open": open_price,
            "High": np.maximum(open_price, close) + 1,
            "Low": np.minimum(open_price, close) - 1,
            "Close": close,
            "Volume": 10_000 + ((step % 100) * 10),
        },
        index=index,
    )


@pytest.fixture
def backtest_stats() -> pd.Series:
    """Servis ve metrik testlerinde kullanılan resmî anahtarlı stats."""
    return pd.Series(
        {
            "Equity Final [$]": np.float64(108_500),
            "Return [%]": np.float64(8.5),
            "Buy & Hold Return [%]": np.float64(6.25),
            "# Trades": np.int64(4),
            "Win Rate [%]": np.float64(50),
            "Max. Drawdown [%]": np.float64(-3.5),
            "Sharpe Ratio": np.float64(1.1),
            "Sortino Ratio": np.float64(1.4),
            "Profit Factor": np.float64(1.7),
            "Best Trade [%]": np.float64(4.2),
            "Worst Trade [%]": np.float64(-2.1),
            "Avg. Trade Duration": pd.Timedelta(days=8),
            "Exposure Time [%]": np.float64(42),
        }
    )
