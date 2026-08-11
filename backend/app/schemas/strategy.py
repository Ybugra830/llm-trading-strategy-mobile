"""Strateji üretim API şemaları."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints


StrategyPrompt = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=5, max_length=2000),
]


class StrategyGenerateRequest(BaseModel):
    """Doğal dilde strateji üretim isteği."""

    prompt: StrategyPrompt


class StrategyGenerateResponse(BaseModel):
    """LLM tarafından üretilen strateji kodu."""

    code: str
    model: str
