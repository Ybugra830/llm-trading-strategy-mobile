"""Statik strateji doğrulama servisi."""

from dataclasses import dataclass

from app.schemas.validation import StrategyValidationResponse
from app.validators.code_cleaner import clean_code
from app.validators.validation_pipeline import validate_strategy_code


@dataclass(frozen=True)
class PreparedStrategyValidation:
    """Temiz kaynak kodu ve ona ait statik doğrulama sonucunu birlikte taşır."""

    code: str
    validation: StrategyValidationResponse


class ValidationService:
    """Kaynak kodunu temizleyip statik doğrulama pipeline'ına yönlendirir."""

    def validate(self, code: str) -> StrategyValidationResponse:
        """Kaynak kodunu çalıştırmadan doğrulama sonucunu döndür."""
        return self.prepare(code).validation

    def prepare(self, code: str) -> PreparedStrategyValidation:
        """Kodu temizle ve aynı temiz sürümün doğrulama sonucunu döndür."""
        cleaned_code = clean_code(code)
        return PreparedStrategyValidation(
            code=cleaned_code,
            validation=validate_strategy_code(cleaned_code),
        )
