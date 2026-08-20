"""Yahoo Finance üzerinden tamamlanmış günlük BIST verisi indirir."""

import logging
from collections.abc import Callable
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

from app.market.errors import MarketDataUnavailableError

logger = logging.getLogger(__name__)
BIST_TIMEZONE = ZoneInfo("Europe/Istanbul")


def bist_today() -> date:
    """BIST yerel takvimindeki bugünün tarihini döndür."""
    return datetime.now(BIST_TIMEZONE).date()


class YahooFinanceProvider:
    """Ham Yahoo Finance DataFrame'ini indiren senkron provider."""

    def __init__(
        self,
        today_provider: Callable[[], date] = bist_today,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._today_provider = today_provider
        self._timeout_seconds = timeout_seconds

    def download_daily(self, yahoo_symbol: str) -> pd.DataFrame:
        """Yaklaşık üç yıllık tamamlanmış günlük barları indir."""
        end_date = self._today_provider()
        start_date = (pd.Timestamp(end_date) - pd.DateOffset(years=3)).date()

        try:
            data = yf.download(
                tickers=yahoo_symbol,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
                interval="1d",
                auto_adjust=True,
                actions=False,
                progress=False,
                threads=False,
                multi_level_index=False,
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            logger.warning(
                "Yahoo Finance download failed ticker=%s error_type=%s",
                yahoo_symbol,
                type(exc).__name__,
            )
            raise MarketDataUnavailableError from exc

        if data is None or data.empty:
            logger.warning("Yahoo Finance returned empty data ticker=%s", yahoo_symbol)
            raise MarketDataUnavailableError

        return data
