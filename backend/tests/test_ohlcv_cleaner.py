"""OHLCV kolon, tarih ve piyasa yapısı temizleme testleri."""

import numpy as np
import pandas as pd
import pytest

from app.market.errors import InvalidMarketDataError
from app.market.ohlcv_cleaner import REQUIRED_OHLCV_COLUMNS, clean_ohlcv


def test_cleaner_returns_required_columns_without_mutating_input(
    ohlcv_data: pd.DataFrame,
) -> None:
    original = ohlcv_data.assign(Extra="ignored")
    snapshot = original.copy(deep=True)

    cleaned = clean_ohlcv(original)

    assert list(cleaned.columns) == list(REQUIRED_OHLCV_COLUMNS)
    assert cleaned is not original
    pd.testing.assert_frame_equal(original, snapshot)


def test_simple_columns_are_normalized_case_insensitively(
    ohlcv_data: pd.DataFrame,
) -> None:
    raw = ohlcv_data.head(3).copy()
    raw.columns = [" open ", "HIGH", "low", "Close", "volume"]

    cleaned = clean_ohlcv(raw)

    assert list(cleaned.columns) == list(REQUIRED_OHLCV_COLUMNS)


@pytest.mark.parametrize("price_level", [0, 1])
def test_yfinance_multiindex_columns_are_normalized(
    ohlcv_data: pd.DataFrame,
    price_level: int,
) -> None:
    raw = ohlcv_data.head(3).copy()
    if price_level == 0:
        raw.columns = pd.MultiIndex.from_tuples(
            [(column, "THYAO.IS") for column in raw.columns]
        )
    else:
        raw.columns = pd.MultiIndex.from_tuples(
            [("THYAO.IS", column) for column in raw.columns]
        )

    cleaned = clean_ohlcv(raw)

    assert list(cleaned.columns) == list(REQUIRED_OHLCV_COLUMNS)


def test_numeric_conversion_sorting_duplicate_and_missing_cleanup() -> None:
    raw = pd.DataFrame(
        {
            "Open": ["12", "10", "11", "bad", "14"],
            "High": ["13", "11", "12", "15", np.inf],
            "Low": ["11", "9", "10", "13", "12"],
            "Close": ["12.5", "10.5", "11.5", "14", "13"],
            "Volume": ["120", "100", "110", "130", "140"],
        },
        index=[
            "2026-01-03",
            "2026-01-01",
            "2026-01-01",
            "not-a-date",
            "2026-01-04",
        ],
    )

    cleaned = clean_ohlcv(raw)

    assert list(cleaned.index) == [
        pd.Timestamp("2026-01-01"),
        pd.Timestamp("2026-01-03"),
    ]
    assert cleaned.loc[pd.Timestamp("2026-01-01"), "Open"] == 11
    assert all(pd.api.types.is_numeric_dtype(cleaned[column]) for column in cleaned)


def test_timezone_is_removed_without_changing_local_calendar_date(
    ohlcv_data: pd.DataFrame,
) -> None:
    raw = ohlcv_data.head(2).copy()
    raw.index = pd.DatetimeIndex(
        ["2026-01-05 00:00:00", "2026-01-06 00:00:00"],
        tz="Europe/Istanbul",
    )

    cleaned = clean_ohlcv(raw)

    assert cleaned.index.tz is None
    assert cleaned.index[0] == pd.Timestamp("2026-01-05")


def test_missing_required_column_is_rejected(ohlcv_data: pd.DataFrame) -> None:
    with pytest.raises(InvalidMarketDataError):
        clean_ohlcv(ohlcv_data.drop(columns="Volume"))


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("Open", 0),
        ("Close", -1),
        ("Volume", -1),
    ],
)
def test_non_positive_prices_and_negative_volume_are_rejected(
    ohlcv_data: pd.DataFrame,
    column: str,
    value: float,
) -> None:
    raw = ohlcv_data.head(3).copy()
    raw.iloc[0, raw.columns.get_loc(column)] = value

    with pytest.raises(InvalidMarketDataError):
        clean_ohlcv(raw)


@pytest.mark.parametrize(
    ("high", "low", "open_price", "close"),
    [
        (9, 10, 9.5, 9.5),
        (10, 8, 11, 9),
        (10, 8, 9, 11),
        (12, 10, 9, 11),
        (12, 10, 11, 9),
    ],
)
def test_impossible_ohlc_relationships_are_rejected(
    high: float,
    low: float,
    open_price: float,
    close: float,
) -> None:
    raw = pd.DataFrame(
        {
            "Open": [open_price],
            "High": [high],
            "Low": [low],
            "Close": [close],
            "Volume": [100],
        },
        index=pd.DatetimeIndex(["2026-01-05"]),
    )

    with pytest.raises(InvalidMarketDataError):
        clean_ohlcv(raw)
