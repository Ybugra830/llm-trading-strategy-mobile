"""Statik strateji doğrulama servisi."""

from app.schemas.validation import StrategyValidationResponse
from app.validators.code_cleaner import clean_code
from app.validators.validation_pipeline import validate_strategy_code


class ValidationService:
    """Kaynak kodunu temizleyip statik doğrulama pipeline'ına yönlendirir."""

    def validate(self, code: str) -> StrategyValidationResponse:
        """Kaynak kodunu çalıştırmadan doğrulama sonucunu döndür."""
        return validate_strategy_code(clean_code(code))
