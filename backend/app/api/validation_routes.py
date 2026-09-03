"""Statik strateji doğrulama endpoint'i."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.schemas.validation import StrategyValidationRequest, StrategyValidationResponse
from app.services.validation_service import ValidationService

router = APIRouter(prefix="/api/v1/strategies", tags=["strategies"])


def get_validation_service() -> ValidationService:
    """İstek için statik doğrulama servisini oluştur."""
    return ValidationService()


@router.post(
    "/validate",
    response_model=StrategyValidationResponse,
    status_code=status.HTTP_200_OK,
)
def validate_strategy(
    request: StrategyValidationRequest,
    service: Annotated[ValidationService, Depends(get_validation_service)],
) -> StrategyValidationResponse:
    """Python kaynak kodunu çalıştırmadan statik olarak doğrula."""
    return service.validate(request.code, request.prompt)
