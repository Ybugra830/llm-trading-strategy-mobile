"""Statik strateji doğrulama servisi."""

from dataclasses import dataclass

from app.schemas.validation import StrategyValidationResponse
from app.validators.code_cleaner import clean_code
from app.validators.validation_pipeline import validate_strategy_code
from app.validators.strategy_contract import analyze_contract, ContractFinding, StrategyRequirements


@dataclass(frozen=True)
class PreparedStrategyValidation:
    """Temiz kaynak kodu ve ona ait statik doğrulama sonucunu birlikte taşır."""

    code: str
    validation: StrategyValidationResponse
    contract_findings: tuple[ContractFinding, ...] = ()
    requirements: StrategyRequirements = StrategyRequirements()


class ValidationService:
    """Kaynak kodunu temizleyip statik doğrulama pipeline'ına yönlendirir."""

    def validate(self, code: str, prompt: str | None = None) -> StrategyValidationResponse:
        """Kaynak kodunu çalıştırmadan doğrulama sonucunu döndür."""
        return self.prepare(code, prompt).validation

    def prepare(self, code: str, prompt: str | None = None) -> PreparedStrategyValidation:
        """Kodu temizle ve aynı temiz sürümün doğrulama sonucunu döndür."""
        cleaned_code = clean_code(code)
        contract = analyze_contract(cleaned_code, prompt)
        return PreparedStrategyValidation(
            code=cleaned_code,
            validation=validate_strategy_code(cleaned_code, contract_findings=contract.findings),
            contract_findings=contract.findings,
            requirements=contract.requirements,
        )
