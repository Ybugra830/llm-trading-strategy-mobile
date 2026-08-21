"""Generated strategy için güvenli end-to-end Strategy Lab orkestrasyonu."""

import asyncio
import hashlib
from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from app.market.bist_symbols import normalize_bist_symbol, to_yahoo_symbol
from app.market.data_split import MarketDataSplit, split_market_data
from app.market.ohlcv_cleaner import clean_ohlcv
from app.runtime.base import SandboxExecutor
from app.runtime.errors import (
    FrozenStrategyExecutionError,
    SandboxUnavailableError,
    StrategyPretestError,
)
from app.runtime.models import FrozenStrategy, SandboxErrorCode, SandboxResult
from app.schemas.backtest import BacktestDataSummary
from app.schemas.strategy_lab import (
    StrategyLabConfiguration,
    StrategyLabGeneration,
    StrategyLabRunRequest,
    StrategyLabRunResponse,
    StrategyLabRuntime,
)
from app.services.strategy_service import StrategyService
from app.services.validation_service import ValidationService

SAFE_SMOKE_ERRORS = {
    SandboxErrorCode.STRATEGY_IMPORT_ERROR: "GeneratedStrategy modülü güvenli runtime testinde yüklenemedi.",
    SandboxErrorCode.STRATEGY_CLASS_MISSING: "Gerekli GeneratedStrategy sınıfı güvenli runtime testinde bulunamadı.",
    SandboxErrorCode.STRATEGY_INTERFACE_ERROR: "GeneratedStrategy arayüzü güvenli runtime testiyle uyumlu değil.",
    SandboxErrorCode.STRATEGY_RUNTIME_ERROR: "GeneratedStrategy güvenli runtime testinde çalıştırılamadı.",
    SandboxErrorCode.STRATEGY_TIMEOUT: "GeneratedStrategy güvenli runtime testinde süre sınırını aştı.",
    SandboxErrorCode.STRATEGY_RESOURCE_LIMIT: "GeneratedStrategy güvenli runtime testinde kaynak sınırını aştı.",
}


class MarketDataProvider(Protocol):
    def download_daily(self, yahoo_symbol: str) -> pd.DataFrame: ...


@dataclass(frozen=True)
class PreparedMarketData:
    clean_data: pd.DataFrame
    split: MarketDataSplit


class StrategyLabService:
    """Repair yalnızca held-out veriden önce yapılacak şekilde akışı yönetir."""

    def __init__(
        self,
        strategy_service: StrategyService,
        validation_service: ValidationService,
        sandbox_executor: SandboxExecutor,
        market_provider: MarketDataProvider,
        max_strategy_versions: int = 3,
    ) -> None:
        self._strategy_service = strategy_service
        self._validation_service = validation_service
        self._sandbox_executor = sandbox_executor
        self._market_provider = market_provider
        self._max_strategy_versions = max_strategy_versions

    async def run(self, request: StrategyLabRunRequest) -> StrategyLabRunResponse:
        symbol = normalize_bist_symbol(request.symbol)
        yahoo_symbol = to_yahoo_symbol(symbol)
        generated = await self._strategy_service.generate(request.prompt)
        attempt_count = 1

        while True:
            prepared = self._validation_service.prepare(generated.code)
            if not prepared.validation.valid:
                generated, attempt_count = await self._repair_or_fail(
                    request.prompt,
                    prepared.code,
                    prepared.validation.errors,
                    attempt_count,
                )
                continue

            code_hash = hashlib.sha256(prepared.code.encode("utf-8")).hexdigest()
            smoke = await asyncio.to_thread(
                self._sandbox_executor.run_smoke,
                prepared.code,
                code_hash,
                request.initial_cash,
                request.commission,
            )
            if not smoke.success:
                safe_error = SAFE_SMOKE_ERRORS.get(smoke.error_code)
                if safe_error is None:
                    raise SandboxUnavailableError
                generated, attempt_count = await self._repair_or_fail(
                    request.prompt,
                    prepared.code,
                    [safe_error],
                    attempt_count,
                )
                continue

            frozen = FrozenStrategy(
                code=prepared.code,
                sha256=code_hash,
                model=generated.model,
                attempt_count=attempt_count,
                validation=prepared.validation,
            )
            break

        market = await asyncio.to_thread(self._prepare_market_data, yahoo_symbol)
        result = await asyncio.to_thread(
            self._sandbox_executor.run_backtest,
            frozen.code,
            frozen.sha256,
            market.split.test_data,
            request.initial_cash,
            request.commission,
        )
        if not result.success:
            if result.error_code in SAFE_SMOKE_ERRORS:
                raise FrozenStrategyExecutionError
            raise SandboxUnavailableError
        if result.strategy_code_hash != frozen.sha256 or result.metrics is None:
            raise SandboxUnavailableError

        return StrategyLabRunResponse(
            generation=StrategyLabGeneration(
                model=frozen.model,
                attempt_count=frozen.attempt_count,
                repaired=frozen.attempt_count > 1,
                code=frozen.code,
            ),
            validation=frozen.validation,
            runtime=StrategyLabRuntime(),
            symbol=symbol,
            yahoo_symbol=yahoo_symbol,
            data=self._data_summary(market),
            configuration=StrategyLabConfiguration(
                initial_cash=request.initial_cash,
                commission=request.commission,
            ),
            metrics=result.metrics,
        )

    async def _repair_or_fail(
        self,
        original_prompt: str,
        current_code: str,
        safe_errors: list[str],
        attempt_count: int,
    ):
        if attempt_count >= self._max_strategy_versions:
            raise StrategyPretestError
        repaired = await self._strategy_service.repair(
            original_prompt,
            current_code,
            [" ".join(error.split())[:300] for error in safe_errors[:10]],
        )
        return repaired, attempt_count + 1

    def _prepare_market_data(self, yahoo_symbol: str) -> PreparedMarketData:
        raw_data = self._market_provider.download_daily(yahoo_symbol)
        clean_data = clean_ohlcv(raw_data)
        return PreparedMarketData(
            clean_data=clean_data,
            split=split_market_data(clean_data),
        )

    @staticmethod
    def _data_summary(market: PreparedMarketData) -> BacktestDataSummary:
        clean_data = market.clean_data
        split = market.split
        return BacktestDataSummary(
            download_start=clean_data.index.min().date(),
            download_end=clean_data.index.max().date(),
            total_rows=len(clean_data),
            history_rows=len(split.history_data),
            test_rows=len(split.test_data),
            cutoff_date=split.cutoff_date.date(),
            test_start=split.test_data.index.min().date(),
            test_end=split.test_data.index.max().date(),
        )
