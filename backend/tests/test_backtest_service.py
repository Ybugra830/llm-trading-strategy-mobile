"""Day 4 servis orkestrasyonu ve yalnızca test-data kullanımı testleri."""

import pandas as pd

from app.backtest.reference_strategies import ReferenceSmaCrossStrategy
from app.market.data_split import split_market_data
from app.schemas.backtest import BistBacktestRequest
from app.services.backtest_service import BacktestService


class FakeProvider:
    def __init__(self, data: pd.DataFrame) -> None:
        self.data = data
        self.requested_symbol: str | None = None

    def download_daily(self, yahoo_symbol: str) -> pd.DataFrame:
        self.requested_symbol = yahoo_symbol
        return self.data


def test_service_runs_only_last_six_month_test_data(
    ohlcv_data: pd.DataFrame,
    backtest_stats: pd.Series,
) -> None:
    provider = FakeProvider(ohlcv_data)
    captured: dict[str, object] = {}

    def recording_runner(
        data: pd.DataFrame,
        strategy_class: type,
        initial_cash: float,
        commission: float,
    ) -> pd.Series:
        captured.update(
            data=data.copy(),
            strategy_class=strategy_class,
            initial_cash=initial_cash,
            commission=commission,
        )
        return backtest_stats

    service = BacktestService(provider, runner=recording_runner)
    response = service.run_bist_backtest(
        BistBacktestRequest(
            symbol=" thyao ",
            initial_cash=120_000,
            commission=0.003,
        )
    )
    expected_split = split_market_data(ohlcv_data)

    assert provider.requested_symbol == "THYAO.IS"
    pd.testing.assert_frame_equal(captured["data"], expected_split.test_data)
    assert captured["strategy_class"] is ReferenceSmaCrossStrategy
    assert captured["initial_cash"] == 120_000
    assert captured["commission"] == 0.003
    assert response.symbol == "THYAO"
    assert response.yahoo_symbol == "THYAO.IS"
    assert response.data.history_rows == len(expected_split.history_data)
    assert response.data.test_rows == len(expected_split.test_data)
    assert response.configuration.strategy == "reference_sma_cross"
    assert response.metrics.net_profit == -11_500
