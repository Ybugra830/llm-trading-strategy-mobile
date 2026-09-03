"""Generated strategy için güvenli end-to-end Strategy Lab orkestrasyonu."""

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from typing import Protocol

import pandas as pd

from app.llm.repair_context import (
    RepairFailureContext,
    build_repair_context,
    static_failure_type,
)
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
from app.services.strategy_lab_observer import StrategyLabAttemptObserver
from app.services.validation_service import ValidationService

logger = logging.getLogger(__name__)

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
        observer: StrategyLabAttemptObserver | None = None,
    ) -> None:
        self._strategy_service = strategy_service
        self._validation_service = validation_service
        self._sandbox_executor = sandbox_executor
        self._market_provider = market_provider
        self._max_strategy_versions = max_strategy_versions
        self._observer = observer

    async def run(self, request: StrategyLabRunRequest) -> StrategyLabRunResponse:
        symbol = normalize_bist_symbol(request.symbol)
        yahoo_symbol = to_yahoo_symbol(symbol)
        generated = await self._strategy_service.generate(request.prompt)
        attempt_count = 1
        if self._observer is not None:
            self._observer.on_generated(attempt_count, "initial", generated)
        logger.info(
            "Strategy Lab generated attempt=%s model=%s",
            attempt_count,
            generated.model,
        )

        while True:
            prepared = self._validation_service.prepare(generated.code, request.prompt)
            if self._observer is not None:
                self._observer.on_validation(
                    attempt_count, prepared.code, prepared.validation
                )
            logger.info(
                "Strategy Lab static validation attempt=%s model=%s valid=%s errors=%s",
                attempt_count,
                generated.model,
                prepared.validation.valid,
                prepared.validation.errors,
            )
            if not prepared.validation.valid:
                context = build_repair_context(
                    stage="static",
                    failure_type=static_failure_type(prepared.validation),
                    code=prepared.code,
                    prompt=request.prompt,
                    safe_findings=prepared.validation.errors,
                    contract_findings=prepared.contract_findings,
                )
                generated, attempt_count = await self._repair_or_fail(
                    request.prompt,
                    prepared.code,
                    context,
                    attempt_count,
                )
                continue

            code_hash = hashlib.sha256(prepared.code.encode("utf-8")).hexdigest()
            logger.info(
                "Strategy Lab sandbox request attempt=%s stage=smoke code_hash_prefix=%s",
                attempt_count,
                code_hash[:12],
            )
            smoke = await asyncio.to_thread(
                self._sandbox_executor.run_smoke,
                prepared.code,
                code_hash,
                request.initial_cash,
                request.commission,
            )
            if self._observer is not None:
                self._observer.on_smoke(attempt_count, smoke)
            logger.info(
                "Strategy Lab sandbox result attempt=%s stage=%s success=%s "
                "error_code=%s error_message=%s",
                attempt_count,
                smoke.stage,
                smoke.success,
                smoke.error_code,
                smoke.error_message,
            )
            if not smoke.success:
                safe_error = SAFE_SMOKE_ERRORS.get(smoke.error_code)
                if safe_error is None:
                    raise SandboxUnavailableError
                context = build_repair_context(
                    stage="smoke",
                    failure_type=(
                        smoke.safe_failure_type.value
                        if smoke.safe_failure_type is not None
                        else smoke.error_code.value
                    ),
                    code=prepared.code,
                    prompt=request.prompt,
                    safe_findings=[safe_error],
                    runtime_context=smoke.safe_failure_context,
                )
                generated, attempt_count = await self._repair_or_fail(
                    request.prompt,
                    prepared.code,
                    context,
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
            logger.info(
                "Strategy Lab strategy frozen attempt=%s model=%s code_hash_prefix=%s",
                attempt_count,
                generated.model,
                code_hash[:12],
            )
            break

        logger.info("Strategy Lab market data request yahoo_symbol=%s", yahoo_symbol)
        market = await asyncio.to_thread(self._prepare_market_data, yahoo_symbol)
        logger.info(
            "Strategy Lab sandbox request stage=backtest code_hash_prefix=%s test_rows=%s",
            frozen.sha256[:12],
            len(market.split.test_data),
        )
        result = await asyncio.to_thread(
            self._sandbox_executor.run_backtest,
            frozen.code,
            frozen.sha256,
            market.split.test_data,
            request.initial_cash,
            request.commission,
        )
        if self._observer is not None:
            self._observer.on_backtest(result)
        logger.info(
            "Strategy Lab sandbox result stage=%s success=%s error_code=%s "
            "error_message=%s",
            result.stage,
            result.success,
            result.error_code,
            result.error_message,
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
        context: RepairFailureContext,
        attempt_count: int,
    ):
        if attempt_count >= self._max_strategy_versions:
            logger.warning(
                "Strategy Lab pretest exhausted attempt=%s max_versions=%s errors=%s",
                attempt_count,
                self._max_strategy_versions,
                context.safe_findings,
            )
            raise StrategyPretestError
        logger.info(
            "Strategy Lab repair requested failed_attempt=%s next_attempt=%s reason=%s",
            attempt_count,
            attempt_count + 1,
            context.safe_findings,
        )
        if self._observer is not None:
            self._observer.on_repair_requested(
                attempt_count, attempt_count + 1, context
            )
        repaired = await self._strategy_service.repair(
            original_prompt,
            current_code,
            context,
        )
        if self._observer is not None:
            self._observer.on_generated(attempt_count + 1, "repair", repaired)
        logger.info(
            "Strategy Lab repair completed attempt=%s model=%s",
            attempt_count + 1,
            repaired.model,
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
