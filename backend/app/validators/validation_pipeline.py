"""Statik strateji doğrulayıcılarını tek AST üzerinde çalıştırır."""

from app.schemas.validation import StrategyValidationResponse
from app.validators.import_validator import validate_imports
from app.validators.interface_validator import validate_interface
from app.validators.lookahead_validator import validate_lookahead
from app.validators.security_validator import validate_security
from app.validators.syntax_validator import parse_syntax


def _unique_errors(errors: list[str]) -> list[str]:
    return list(dict.fromkeys(errors))


def validate_strategy_code(code: str) -> StrategyValidationResponse:
    """Kaynak kodunu bir kez parse edip tüm statik kontrolleri çalıştır."""
    syntax_result = parse_syntax(code)
    if not syntax_result.valid or syntax_result.tree is None:
        return StrategyValidationResponse(
            valid=False,
            syntax_valid=False,
            imports_valid=False,
            security_valid=False,
            interface_valid=False,
            lookahead_valid=False,
            errors=syntax_result.errors,
        )

    import_errors = validate_imports(syntax_result.tree)
    security_errors = validate_security(syntax_result.tree)
    interface_errors = validate_interface(syntax_result.tree)
    lookahead_errors = validate_lookahead(syntax_result.tree)
    errors = _unique_errors(
        import_errors + security_errors + interface_errors + lookahead_errors
    )

    imports_valid = not import_errors
    security_valid = not security_errors
    interface_valid = not interface_errors
    lookahead_valid = not lookahead_errors
    valid = all(
        (
            syntax_result.valid,
            imports_valid,
            security_valid,
            interface_valid,
            lookahead_valid,
        )
    )

    return StrategyValidationResponse(
        valid=valid,
        syntax_valid=True,
        imports_valid=imports_valid,
        security_valid=security_valid,
        interface_valid=interface_valid,
        lookahead_valid=lookahead_valid,
        errors=errors,
    )
