"""Strateji üretim endpoint'i."""

from typing import Annotated
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.llm.nvidia_client import NvidiaNimClient, NvidiaNimError
from app.schemas.strategy import StrategyGenerateRequest, StrategyGenerateResponse
from app.services.strategy_service import StrategyService
from app.services.admission_service import StrategyAdmissionError
from app.schemas.admission import AdmissionFailure
from app.execution_trace import failure

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


async def get_strategy_service() -> AsyncIterator[StrategyService]:
    """İstek için strateji servisini oluştur."""
    async with NvidiaNimClient(get_settings()) as client:
        yield StrategyService(client)


@router.post(
    "/generate",
    response_model=StrategyGenerateResponse,
    response_model_exclude_none=True,
    responses={422: {"model": AdmissionFailure}},
    status_code=status.HTTP_200_OK,
)
async def generate_strategy(
    request: StrategyGenerateRequest,
    service: Annotated[StrategyService, Depends(get_strategy_service)],
) -> StrategyGenerateResponse | JSONResponse:
    """Doğal dil strateji isteğinden Python kodu üret."""
    try:
        return await service.generate(request.prompt)
    except StrategyAdmissionError as exc:
        return JSONResponse(status_code=422, content=exc.failure.model_dump())
    except NvidiaNimError as exc:
        failure('NVIDIA_' + exc.kind.value.upper())
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Strateji şu anda oluşturulamıyor.",
        ) from exc
