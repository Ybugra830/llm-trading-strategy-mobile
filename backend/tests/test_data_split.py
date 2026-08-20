"""Altı takvim aylık kronolojik piyasa verisi split testleri."""

import pandas as pd
import pytest

from app.market.data_split import MINIMUM_TEST_BARS, split_market_data
from app.market.errors import InsufficientMarketDataError, InvalidMarketDataError


def test_split_uses_latest_date_and_never_overlaps(
    ohlcv_data: pd.DataFrame,
) -> None:
    split = split_market_data(ohlcv_data)
    expected_cutoff = ohlcv_data.index.max() - pd.DateOffset(months=6)

    assert split.cutoff_date == expected_cutoff
    assert (split.history_data.index < expected_cutoff).all()
    assert (split.test_data.index >= expected_cutoff).all()
    assert split.history_data.index.intersection(split.test_data.index).empty
    assert split.history_data.index.is_monotonic_increasing
    assert split.test_data.index.is_monotonic_increasing
    assert len(split.test_data) >= MINIMUM_TEST_BARS


def test_split_returns_copies(ohlcv_data: pd.DataFrame) -> None:
    split = split_market_data(ohlcv_data)
    original = ohlcv_data.iloc[-1]["Close"]

    split.test_data.iloc[-1, split.test_data.columns.get_loc("Close")] = -99

    assert ohlcv_data.iloc[-1]["Close"] == original


def test_split_rejects_empty_history(ohlcv_data: pd.DataFrame) -> None:
    with pytest.raises(InsufficientMarketDataError):
        split_market_data(ohlcv_data.tail(80))


def test_split_rejects_fewer_than_sixty_test_bars(
    ohlcv_data: pd.DataFrame,
) -> None:
    latest = ohlcv_data.index.max()
    cutoff = latest - pd.DateOffset(months=6)
    history = ohlcv_data.loc[ohlcv_data.index < cutoff].tail(100)
    test = ohlcv_data.loc[ohlcv_data.index >= cutoff].tail(MINIMUM_TEST_BARS - 1)
    too_short = pd.concat([history, test]).sort_index()

    with pytest.raises(InsufficientMarketDataError):
        split_market_data(too_short)


def test_split_rejects_unsorted_input(ohlcv_data: pd.DataFrame) -> None:
    with pytest.raises(InvalidMarketDataError):
        split_market_data(ohlcv_data.iloc[::-1])
