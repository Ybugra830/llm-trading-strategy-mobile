"""Trusted repository-owned stratejiyle BIST backtest endpoint'i."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.backtest.errors import BacktestExecutionError
from app.market.errors import (
    InsufficientMarketDataError,
    InvalidMarketDataError,
    MarketDataUnavailableError,
    UnsupportedBistSymbolError,
)
from app.market.yahoo_provider import YahooFinanceProvider
from app.schemas.backtest import BistBacktestRequest, BistBacktestResponse
from app.services.backtest_service import BacktestService

router = APIRouter(prefix="/api/v1/backtests", tags=["backtests"])


def get_backtest_service() -> BacktestService:
    """İstek için production Yahoo provider kullanan servisi oluştur."""
    return BacktestService(YahooFinanceProvider())


@router.post(
    "/bist",
    response_model=BistBacktestResponse,
    status_code=status.HTTP_200_OK,
)
def run_bist_backtest(
    request: BistBacktestRequest,
    service: Annotated[BacktestService, Depends(get_backtest_service)],
) -> BistBacktestResponse:
    """Tamamlanmış BIST barlarında güvenilir referans stratejiyi test et."""
    try:
        return service.run_bist_backtest(request)
    except UnsupportedBistSymbolError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Desteklenmeyen BIST sembolü.",
        ) from exc
    except InsufficientMarketDataError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Backtest için yeterli piyasa verisi bulunamadı.",
        ) from exc
    except (MarketDataUnavailableError, InvalidMarketDataError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Piyasa verisi şu anda kullanılamıyor.",
        ) from exc
    except BacktestExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Backtest şu anda çalıştırılamıyor.",
        ) from exc
