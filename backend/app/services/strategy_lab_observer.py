"""Optional internal observer for opt-in Strategy Lab reliability diagnostics."""

from typing import Literal, Protocol

from app.runtime.models import SandboxResult
from app.llm.repair_context import RepairFailureContext
from app.schemas.strategy import StrategyGenerateResponse
from app.schemas.validation import StrategyValidationResponse


GenerationSource = Literal["initial", "repair"]


class StrategyLabAttemptObserver(Protocol):
    def on_generated(
        self,
        attempt: int,
        source: GenerationSource,
        generated: StrategyGenerateResponse,
    ) -> None: ...

    def on_validation(
        self,
        attempt: int,
        code: str,
        validation: StrategyValidationResponse,
    ) -> None: ...

    def on_smoke(self, attempt: int, result: SandboxResult) -> None: ...

    def on_repair_requested(
        self,
        failed_attempt: int,
        next_attempt: int,
        context: RepairFailureContext,
    ) -> None: ...

    def on_backtest(self, result: SandboxResult) -> None: ...
