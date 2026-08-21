"""Sandbox executor bağımlılık sınırı."""

from typing import Protocol

import pandas as pd

from app.runtime.models import SandboxResult


class SandboxExecutor(Protocol):
    """Generated source'u yalnızca izole runtime'a aktaran arayüz."""

    def run_smoke(
        self,
        code: str,
        strategy_code_hash: str,
        initial_cash: float,
        commission: float,
    ) -> SandboxResult: ...

    def run_backtest(
        self,
        code: str,
        strategy_code_hash: str,
        data: pd.DataFrame,
        initial_cash: float,
        commission: float,
    ) -> SandboxResult: ...
