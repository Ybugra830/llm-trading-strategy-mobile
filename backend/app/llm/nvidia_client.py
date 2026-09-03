"""Bounded NVIDIA NIM generation with safe errors and explicit model profiles."""

import asyncio
import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from time import perf_counter

import httpx
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, OpenAIError

from app.config import Settings
from app.llm.nvidia_options import get_model_options
from app.llm.prompt_builder import build_repair_messages, build_strategy_messages
from app.llm.repair_context import RepairFailureContext

logger = logging.getLogger(__name__)


class ProviderErrorKind(StrEnum):
    AUTHENTICATION = "authentication_failure"
    PERMISSION = "permission_denied"
    MODEL_UNAVAILABLE = "model_unavailable"
    RATE_LIMIT = "provider_rate_limit"
    TIMEOUT = "provider_timeout"
    SERVER = "provider_5xx"
    NETWORK = "network_failure"
    INVALID_REQUEST = "invalid_request"
    INVALID_RESPONSE = "invalid_response"
    UNKNOWN = "provider_error"


class NvidiaNimError(RuntimeError):
    """Safe public message plus an internal, structured failure category."""

    def __init__(self, message: str, *, kind: ProviderErrorKind = ProviderErrorKind.UNKNOWN):
        super().__init__(message)
        self.kind = kind


@dataclass(frozen=True)
class ProviderErrorDetails:
    exception_type: str
    status_code: int | None
    request_id: str | None
    message: str
    kind: ProviderErrorKind

    def as_text(self) -> str:
        return (f"category={self.kind.value} type={self.exception_type} "
                f"status={self.status_code if self.status_code is not None else '-'} "
                f"request_id={self.request_id or '-'} message={self.message}")


def get_provider_error_details(
    error: OpenAIError | TimeoutError, *, api_key: str = "",
) -> ProviderErrorDetails:
    """Classify by type/status; never retain raw provider text or headers."""
    status = getattr(error, "status_code", None)
    if isinstance(error, (APITimeoutError, TimeoutError)):
        kind = ProviderErrorKind.TIMEOUT
    elif status == 401:
        kind = ProviderErrorKind.AUTHENTICATION
    elif status == 403:
        kind = ProviderErrorKind.PERMISSION
    elif status in (404, 410):
        kind = ProviderErrorKind.MODEL_UNAVAILABLE
    elif status == 429:
        kind = ProviderErrorKind.RATE_LIMIT
    elif status is not None and 500 <= status <= 599:
        kind = ProviderErrorKind.SERVER
    elif isinstance(error, APIConnectionError):
        kind = ProviderErrorKind.NETWORK
    elif status is not None and 400 <= status <= 499:
        kind = ProviderErrorKind.INVALID_REQUEST
    else:
        kind = ProviderErrorKind.UNKNOWN
    request_id = getattr(error, "request_id", None)
    if (not isinstance(request_id, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", request_id)
            or "nvapi-" in request_id
            or (api_key and api_key in request_id)):
        request_id = None
    return ProviderErrorDetails(type(error).__name__, status, request_id,
                                "Provider request failed.", kind)


class NvidiaNimClient:
    """One request-scoped client, reused for generation, retries and repairs."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: AsyncOpenAI | None = None
        self._last_model = settings.nvidia_model
        self._managed = False

    @property
    def model(self) -> str:
        """Report the successful response's model, including an explicit fallback."""
        return self._last_model

    async def __aenter__(self):
        # Open lazily inside generation so API routes can safely map missing keys.
        self._managed = True
        return self

    def _open_client(self) -> None:
        api_key = self._settings.nvidia_api_key.get_secret_value().strip()
        if not api_key:
            raise NvidiaNimError("NVIDIA API anahtarı yapılandırılmamış.",
                                 kind=ProviderErrorKind.AUTHENTICATION)
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self._settings.nvidia_base_url,
            timeout=httpx.Timeout(
                connect=self._settings.nvidia_connect_timeout_seconds,
                read=self._settings.nvidia_read_timeout_seconds,
                write=self._settings.nvidia_write_timeout_seconds,
                pool=self._settings.nvidia_pool_timeout_seconds,
            ),
            # SDK retries include statuses outside our policy; own them here.
            max_retries=0,
        )

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        client, self._client = self._client, None
        self._managed = False
        if client is not None:
            await client.close()

    async def generate_code(self, prompt: str) -> str:
        return await self._complete(build_strategy_messages(prompt))

    async def repair_code(self, original_prompt: str, current_code: str,
                          context: RepairFailureContext) -> str:
        return await self._complete(build_repair_messages(original_prompt, current_code, context))

    async def _complete(self, messages: list) -> str:
        # Standalone callers remain safe without explicitly opening a context.
        if not self._managed:
            async with self:
                return await self._complete(messages)
        if self._client is None:
            self._open_client()
        primary = self._settings.nvidia_model
        try:
            return await self._complete_model(messages, primary)
        except NvidiaNimError as error:
            fallback = self._settings.nvidia_fallback_model
            if (not fallback or fallback == primary or error.kind not in (
                ProviderErrorKind.MODEL_UNAVAILABLE, ProviderErrorKind.TIMEOUT,
            )):
                raise
            logger.warning("NVIDIA fallback selected primary=%s fallback=%s reason=%s",
                           primary, fallback, error.kind.value)
            # No recursive fallback. It passes through the identical prompt and pipeline.
            return await self._complete_model(messages, fallback)

    async def _complete_model(self, messages: list, model: str) -> str:
        started = perf_counter()
        # Retain a failure while backing off so an exhausted 429/5xx budget
        # cannot accidentally make that failure eligible for model fallback.
        state: dict[str, ProviderErrorKind | None] = {"backoff_failure": None}
        try:
            # Includes network attempts AND backoff: retries cannot reset this budget.
            async with asyncio.timeout(self._settings.nvidia_request_timeout_seconds):
                return await self._attempts(messages, model, state)
        except TimeoutError as error:
            kind = state["backoff_failure"] or ProviderErrorKind.TIMEOUT
            logger.error("NVIDIA NIM request failed model=%s category=%s duration_seconds=%.3f",
                         model, kind.value, perf_counter() - started)
            raise NvidiaNimError("NVIDIA NIM isteği zaman aşımına uğradı.",
                                 kind=kind) from error

    async def _attempts(self, messages: list, model: str,
                        state: dict[str, ProviderErrorKind | None]) -> str:
        assert self._client is not None
        retryable = {ProviderErrorKind.TIMEOUT, ProviderErrorKind.RATE_LIMIT, ProviderErrorKind.SERVER}
        for attempt in range(self._settings.nvidia_max_retries + 1):
            state["backoff_failure"] = None
            started = perf_counter()
            logger.info("NVIDIA NIM attempt started model=%s attempt=%s", model, attempt + 1)
            try:
                completion = await self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=self._settings.nvidia_max_tokens,
                    stream=False,
                    **get_model_options(model),
                )
            except OpenAIError as error:
                details = get_provider_error_details(
                    error, api_key=self._settings.nvidia_api_key.get_secret_value().strip())
                logger.error("NVIDIA NIM request failed model=%s attempt=%s duration_seconds=%.3f %s",
                             model, attempt + 1, perf_counter() - started, details.as_text())
                if details.kind in retryable and attempt < self._settings.nvidia_max_retries:
                    state["backoff_failure"] = details.kind
                    await asyncio.sleep(self._settings.nvidia_retry_backoff_seconds)
                    continue
                raise NvidiaNimError("NVIDIA NIM isteği başarısız oldu.", kind=details.kind) from error
            if not completion.choices:
                logger.warning("NVIDIA NIM empty response model=%s attempt=%s duration_seconds=%.3f",
                               model, attempt + 1, perf_counter() - started)
                raise NvidiaNimError("NVIDIA NIM boş bir yanıt döndürdü.",
                                     kind=ProviderErrorKind.INVALID_RESPONSE)
            content = completion.choices[0].message.content
            if not content or not content.strip():
                logger.warning("NVIDIA NIM empty response model=%s attempt=%s duration_seconds=%.3f",
                               model, attempt + 1, perf_counter() - started)
                raise NvidiaNimError("NVIDIA NIM boş bir yanıt döndürdü.",
                                     kind=ProviderErrorKind.INVALID_RESPONSE)
            self._last_model = getattr(completion, "model", None) or model
            logger.info("NVIDIA NIM request succeeded requested_model=%s returned_model=%s "
                        "attempt=%s duration_seconds=%.3f", model, self._last_model,
                        attempt + 1, perf_counter() - started)
            return content.strip()
        raise AssertionError("Unreachable retry state")
