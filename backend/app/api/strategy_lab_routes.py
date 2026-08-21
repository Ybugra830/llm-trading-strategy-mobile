"""Flutter-facing Strategy Lab endpointleri."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.indicators.registry import SUPPORTED_INDICATORS
from app.llm.nvidia_client import NvidiaNimClient, NvidiaNimError
from app.market.bist_symbols import SUPPORTED_BIST_SYMBOL_ORDER
from app.market.errors import (
    InsufficientMarketDataError,
    InvalidMarketDataError,
    MarketDataUnavailableError,
    UnsupportedBistSymbolError,
)
from app.market.yahoo_provider import YahooFinanceProvider
from app.runtime.docker_executor import DockerSandboxExecutor
from app.runtime.errors import (
    FrozenStrategyExecutionError,
    SandboxUnavailableError,
    StrategyPretestError,
)
from app.schemas.strategy_lab import (
    StrategyLabCapabilitiesResponse,
    StrategyLabDefaults,
    StrategyLabRunRequest,
    StrategyLabRunResponse,
    StrategyPromptLimits,
)
from app.services.strategy_lab_service import StrategyLabService
from app.services.strategy_service import StrategyService
from app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/strategy-lab", tags=["strategy-lab"])


def get_strategy_lab_service() -> StrategyLabService:
    settings = get_settings()
    return StrategyLabService(
        strategy_service=StrategyService(NvidiaNimClient(settings)),
        validation_service=ValidationService(),
        sandbox_executor=DockerSandboxExecutor(settings),
        market_provider=YahooFinanceProvider(),
        max_strategy_versions=settings.max_strategy_versions,
    )


@router.get("/capabilities", response_model=StrategyLabCapabilitiesResponse)
def get_capabilities() -> StrategyLabCapabilitiesResponse:
    return StrategyLabCapabilitiesResponse(
        supported_symbols=list(SUPPORTED_BIST_SYMBOL_ORDER),
        supported_indicators=[item.display_name for item in SUPPORTED_INDICATORS],
        defaults=StrategyLabDefaults(initial_cash=100_000, commission=0.002),
        prompt=StrategyPromptLimits(min_length=5, max_length=2_000),
    )


@router.post(
    "/run",
    response_model=StrategyLabRunResponse,
    status_code=status.HTTP_200_OK,
)
async def run_strategy_lab(
    request: StrategyLabRunRequest,
    service: Annotated[StrategyLabService, Depends(get_strategy_lab_service)],
) -> StrategyLabRunResponse:
    try:
        return await service.run(request)
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
    except StrategyPretestError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Strateji güvenli doğrulama aşamalarını geçemedi.",
        ) from exc
    except FrozenStrategyExecutionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Üretilen strateji gerçek test verisi üzerinde çalıştırılamadı.",
        ) from exc
    except NvidiaNimError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Strateji şu anda oluşturulamıyor.",
        ) from exc
    except (MarketDataUnavailableError, InvalidMarketDataError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Piyasa verisi şu anda kullanılamıyor.",
        ) from exc
    except SandboxUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Güvenli strateji çalışma ortamı şu anda kullanılamıyor.",
        ) from exc
    except Exception as exc:
        logger.error("Strategy Lab failed error_type=%s", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Strategy Lab isteği şu anda tamamlanamıyor.",
        ) from exc
