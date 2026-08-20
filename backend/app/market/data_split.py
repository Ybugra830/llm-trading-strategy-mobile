"""Temiz piyasa verisini kronolojik history ve test bölümlerine ayırır."""

from dataclasses import dataclass

import pandas as pd

from app.market.errors import InsufficientMarketDataError, InvalidMarketDataError

MINIMUM_TEST_BARS = 60


@dataclass(frozen=True)
class MarketDataSplit:
    """Altı aylık test sınırıyla ayrılan piyasa verisi."""

    history_data: pd.DataFrame
    test_data: pd.DataFrame
    cutoff_date: pd.Timestamp


def split_market_data(
    data: pd.DataFrame,
    minimum_test_bars: int = MINIMUM_TEST_BARS,
) -> MarketDataSplit:
    """Son altı takvim ayını görülmemiş test dönemi olarak ayır."""
    if (
        data.empty
        or not isinstance(data.index, pd.DatetimeIndex)
        or not data.index.is_monotonic_increasing
        or data.index.has_duplicates
    ):
        raise InvalidMarketDataError

    latest_market_date = data.index.max()
    cutoff_date = latest_market_date - pd.DateOffset(months=6)
    history_data = data.loc[data.index < cutoff_date].copy()
    test_data = data.loc[data.index >= cutoff_date].copy()

    if history_data.empty or len(test_data) < minimum_test_bars:
        raise InsufficientMarketDataError
    if not history_data.index.intersection(test_data.index).empty:
        raise InvalidMarketDataError

    return MarketDataSplit(
        history_data=history_data,
        test_data=test_data,
        cutoff_date=cutoff_date,
    )
