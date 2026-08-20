"""Yahoo provider tarih politikası ve güvenli hata testleri."""

import logging
from datetime import date

import pandas as pd
import pytest

from app.market.errors import MarketDataUnavailableError
from app.market.yahoo_provider import YahooFinanceProvider


def test_provider_requests_three_years_and_excludes_current_day(
    monkeypatch: pytest.MonkeyPatch,
    ohlcv_data: pd.DataFrame,
) -> None:
    captured: dict[str, object] = {}

    def fake_download(**kwargs: object) -> pd.DataFrame:
        captured.update(kwargs)
        return ohlcv_data

    monkeypatch.setattr("app.market.yahoo_provider.yf.download", fake_download)
    provider = YahooFinanceProvider(today_provider=lambda: date(2026, 8, 18))

    result = provider.download_daily("THYAO.IS")

    assert result is ohlcv_data
    assert captured == {
        "tickers": "THYAO.IS",
        "start": "2023-08-18",
        "end": "2026-08-18",
        "interval": "1d",
        "auto_adjust": True,
        "actions": False,
        "progress": False,
        "threads": False,
        "multi_level_index": False,
        "timeout": 10.0,
    }
    assert captured["end"] != "2026-08-19"


def test_empty_yahoo_result_becomes_application_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "app.market.yahoo_provider.yf.download",
        lambda **_: pd.DataFrame(),
    )

    with pytest.raises(MarketDataUnavailableError):
        YahooFinanceProvider(today_provider=lambda: date(2026, 8, 18)).download_daily(
            "THYAO.IS"
        )


def test_provider_exception_is_logged_without_raw_message(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def fail_download(**_: object) -> pd.DataFrame:
        raise RuntimeError("provider-secret-do-not-log-this-value")

    monkeypatch.setattr("app.market.yahoo_provider.yf.download", fail_download)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(MarketDataUnavailableError):
            YahooFinanceProvider(
                today_provider=lambda: date(2026, 8, 18)
            ).download_daily("THYAO.IS")

    assert "RuntimeError" in caplog.text
    assert "provider-secret-do-not-log-this-value" not in caplog.text
