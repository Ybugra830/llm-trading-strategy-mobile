"""Python kaynak kodunu çalıştırmadan sözdizimi ağacına dönüştürür."""

import ast
from dataclasses import dataclass, field


@dataclass(frozen=True)
class SyntaxValidationResult:
    """Sözdizimi ayrıştırmasının yapılandırılmış sonucu."""

    valid: bool
    tree: ast.Module | None = None
    errors: list[str] = field(default_factory=list)


def parse_syntax(code: str) -> SyntaxValidationResult:
    """Kaynak kodunu yalnızca ``ast.parse`` kullanarak ayrıştır."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return SyntaxValidationResult(
            valid=False,
            errors=[f"Sözdizimi hatası: {exc.msg}"],
        )

    return SyntaxValidationResult(valid=True, tree=tree)
