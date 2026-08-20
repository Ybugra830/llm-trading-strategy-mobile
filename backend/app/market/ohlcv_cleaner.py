"""Yahoo Finance OHLCV DataFrame'ini backtest için normalize eder."""

from collections.abc import Iterable

import numpy as np
import pandas as pd

from app.market.errors import InvalidMarketDataError

REQUIRED_OHLCV_COLUMNS = ("Open", "High", "Low", "Close", "Volume")
_CANONICAL_COLUMNS = {column.casefold(): column for column in REQUIRED_OHLCV_COLUMNS}


def _canonical_name(value: object) -> str:
    text = str(value).strip()
    return _CANONICAL_COLUMNS.get(text.casefold(), text)


def _required_names(values: Iterable[object]) -> set[str]:
    return {
        canonical
        for value in values
        if (canonical := _canonical_name(value)) in REQUIRED_OHLCV_COLUMNS
    }


def _normalize_columns(data: pd.DataFrame) -> pd.DataFrame:
    normalized = data.copy()

    if isinstance(normalized.columns, pd.MultiIndex):
        candidate_levels = [
            level
            for level in range(normalized.columns.nlevels)
            if set(REQUIRED_OHLCV_COLUMNS).issubset(
                _required_names(normalized.columns.get_level_values(level))
            )
        ]
        if len(candidate_levels) != 1:
            raise InvalidMarketDataError
        normalized.columns = [
            _canonical_name(value)
            for value in normalized.columns.get_level_values(candidate_levels[0])
        ]
    else:
        normalized.columns = [_canonical_name(value) for value in normalized.columns]

    required_duplicates = [
        column
        for column in REQUIRED_OHLCV_COLUMNS
        if list(normalized.columns).count(column) > 1
    ]
    if required_duplicates:
        raise InvalidMarketDataError

    if not set(REQUIRED_OHLCV_COLUMNS).issubset(normalized.columns):
        raise InvalidMarketDataError

    return normalized.loc[:, list(REQUIRED_OHLCV_COLUMNS)].copy()


def _normalize_index(data: pd.DataFrame) -> pd.DataFrame:
    normalized = data.copy()
    try:
        parsed_index = pd.DatetimeIndex(pd.to_datetime(normalized.index, errors="coerce"))
    except (TypeError, ValueError) as exc:
        raise InvalidMarketDataError from exc

    if parsed_index.tz is not None:
        parsed_index = parsed_index.tz_localize(None)

    valid_dates = ~parsed_index.isna()
    normalized = normalized.loc[valid_dates].copy()
    normalized.index = parsed_index[valid_dates]
    normalized.index.name = "Date"
    return normalized


def _validate_price_structure(data: pd.DataFrame) -> None:
    prices = data.loc[:, ["Open", "High", "Low", "Close"]]
    if (prices <= 0).any(axis=None):
        raise InvalidMarketDataError
    if (data["Volume"] < 0).any():
        raise InvalidMarketDataError
    if (
        (data["High"] < data["Low"]).any()
        or (data["High"] < data["Open"]).any()
        or (data["High"] < data["Close"]).any()
        or (data["Low"] > data["Open"]).any()
        or (data["Low"] > data["Close"]).any()
    ):
        raise InvalidMarketDataError


def clean_ohlcv(data: pd.DataFrame) -> pd.DataFrame:
    """Ham veriyi temizleyip doğrulanmış, kronolojik OHLCV döndür."""
    if not isinstance(data, pd.DataFrame) or data.empty:
        raise InvalidMarketDataError

    cleaned = _normalize_columns(data)
    cleaned = _normalize_index(cleaned)

    for column in REQUIRED_OHLCV_COLUMNS:
        cleaned[column] = pd.to_numeric(cleaned[column], errors="coerce")

    cleaned = cleaned.replace([np.inf, -np.inf], np.nan)
    cleaned = cleaned.dropna(subset=list(REQUIRED_OHLCV_COLUMNS))
    cleaned = cleaned.loc[~cleaned.index.duplicated(keep="last")]
    cleaned = cleaned.sort_index(kind="mergesort")

    if cleaned.empty:
        raise InvalidMarketDataError

    _validate_price_structure(cleaned)
    return cleaned
