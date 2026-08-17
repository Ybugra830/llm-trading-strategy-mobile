"""Statik strateji doğrulama API şemaları."""

from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


StrategySourceCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=20_000),
]


class StrategyValidationRequest(BaseModel):
    """Doğrulanacak Python kaynak kodu."""

    code: StrategySourceCode


class StrategyValidationResponse(BaseModel):
    """Statik doğrulama aşamalarının birleşik sonucu."""

    valid: bool
    syntax_valid: bool
    imports_valid: bool
    security_valid: bool
    interface_valid: bool
    lookahead_valid: bool
    errors: list[str] = Field(default_factory=list)
