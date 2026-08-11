"""Strateji üretim endpoint'i."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.config import get_settings
from app.llm.nvidia_client import NvidiaNimClient, NvidiaNimError
from app.schemas.strategy import StrategyGenerateRequest, StrategyGenerateResponse
from app.services.strategy_service import StrategyService

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


def get_strategy_service() -> StrategyService:
    """İstek için strateji servisini oluştur."""
    return StrategyService(NvidiaNimClient(get_settings()))


@router.post(
    "/generate",
    response_model=StrategyGenerateResponse,
    status_code=status.HTTP_200_OK,
)
async def generate_strategy(
    request: StrategyGenerateRequest,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
) -> StrategyGenerateResponse:
    """Doğal dil strateji isteğinden Python kodu üret."""
    try:
        return await service.generate(request.prompt)
    except NvidiaNimError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Strateji şu anda oluşturulamıyor.",
        ) from exc
