"""Bounded NVIDIA NIM generation with safe errors and explicit model profiles."""

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from time import perf_counter

import httpx
from openai import APIConnectionError, APITimeoutError, AsyncOpenAI, OpenAIError
from openai import DefaultAsyncHttpxClient, DEFAULT_CONNECTION_LIMITS
from httpx._utils import get_environment_proxies

from app.config import Settings
from app.llm.nvidia_options import get_model_options
from app.llm.admission_prompt import build_admission_messages
from app.llm.prompt_builder import build_repair_messages, build_strategy_messages
from app.llm.repair_context import RepairFailureContext
from app.execution_trace import failure

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

    def __init__(self, message: str, *, kind: ProviderErrorKind = ProviderErrorKind.UNKNOWN,
                 status_code: int | None = None):
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code


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
        self._http_client: httpx.AsyncClient | None = None
        self._last_model = settings.nvidia_model
        self._managed = False
        self.attempt_records: list[dict] = []

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
        timeout = httpx.Timeout(
            connect=self._settings.nvidia_connect_timeout_seconds,
            read=self._settings.nvidia_read_timeout_seconds,
            write=self._settings.nvidia_write_timeout_seconds,
            pool=self._settings.nvidia_pool_timeout_seconds,
        )
        # A custom transport disables HTTPX's environment proxy discovery.
        # Preserve proxy routing when configured; force IPv4 only on direct connections.
        options = {} if any(get_environment_proxies().values()) else {
            "transport": httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=0,
                                                 limits=DEFAULT_CONNECTION_LIMITS),
        }
        self._http_client = DefaultAsyncHttpxClient(timeout=timeout, **options)
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self._settings.nvidia_base_url,
            timeout=timeout,
            http_client=self._http_client,
            # SDK retries include statuses outside our policy; own them here.
            max_retries=0,
        )

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        client, self._client = self._client, None
        self._managed = False
        try:
            if client is not None:
                await client.close()
        finally:
            http, self._http_client = self._http_client, None
            if http is not None and not http.is_closed:
                await http.aclose()

    async def generate_code(self, prompt: str) -> str:
        return await self._complete(build_strategy_messages(prompt))

    async def assess_intent(self, prompt: str) -> str:
        """Assessment uses the same fail-closed policy within a 30-second budget."""
        return await self._complete(build_admission_messages(prompt), stage="assessment")

    async def repair_code(self, original_prompt: str, current_code: str,
                          context: RepairFailureContext) -> str:
        return await self._complete(build_repair_messages(original_prompt, current_code, context), stage="repair")

    async def _complete(self, messages: list, *, stage: str = "generation") -> str:
        # Standalone callers remain safe without explicitly opening a context.
        if not self._managed:
            async with self:
                return await self._complete(messages, stage=stage)
        if self._client is None:
            self._open_client()
        primary = self._settings.nvidia_model
        fallback = self._settings.nvidia_fallback_model
        has_fallback = bool(fallback and fallback != primary)
        budget = self._settings.nvidia_request_timeout_seconds
        if stage == "assessment":
            budget = min(30, budget)
        loop = asyncio.get_running_loop()
        started = loop.time()
        deadline = started + budget
        max_tokens = min(2048, self._settings.nvidia_max_tokens) if stage == "assessment" else self._settings.nvidia_max_tokens
        try:
            return await self._complete_model(messages, primary, deadline=started + budget / 2 if has_fallback else deadline,
                                              max_tokens=max_tokens, stage=stage)
        except NvidiaNimError as error:
            eligible = error.status_code in {404, 410, 429, 500, 502, 503, 504} or (
                error.status_code is None and error.kind in (ProviderErrorKind.TIMEOUT, ProviderErrorKind.NETWORK)
            )
            if not has_fallback or not eligible or loop.time() >= deadline:
                raise
            logger.warning("NVIDIA fallback selected primary=%s fallback=%s reason=%s",
                           primary, fallback, error.kind.value)
            # No recursive fallback. It passes through the identical prompt and pipeline.
            return await self._complete_model(messages, fallback, deadline=deadline,
                                              max_tokens=max_tokens, stage=stage)

    async def _complete_model(self, messages: list, model: str, *, deadline: float,
                              max_tokens: int, stage: str) -> str:
        started = perf_counter()
        # Retain a failure while backing off so an exhausted 429/5xx budget
        # cannot accidentally make that failure eligible for model fallback.
        state: dict[str, ProviderErrorKind | None] = {"backoff_failure": None}
        try:
            # One monotonic deadline includes requests and retry backoff.
            async with asyncio.timeout_at(deadline):
                return await self._attempts(messages, model, state, max_tokens=max_tokens, stage=stage)
        except TimeoutError as error:
            kind = state["backoff_failure"] or ProviderErrorKind.TIMEOUT
            if self.attempt_records and self.attempt_records[-1]["error_kind"] == "cancelled":
                self.attempt_records[-1]["error_kind"] = kind.value
            logger.error("NVIDIA NIM request failed model=%s category=%s duration_seconds=%.3f",
                         model, kind.value, perf_counter() - started)
            raise NvidiaNimError("NVIDIA NIM isteği zaman aşımına uğradı.",
                                 kind=kind) from error

    async def _attempts(self, messages: list, model: str,
                        state: dict[str, ProviderErrorKind | None], *, max_tokens: int,
                        stage: str) -> str:
        assert self._client is not None
        retryable = {ProviderErrorKind.TIMEOUT, ProviderErrorKind.RATE_LIMIT, ProviderErrorKind.SERVER}
        fallback = self._settings.nvidia_fallback_model
        # With a distinct fallback, spend the next attempt on it, never retry either model.
        retries = 0 if fallback and fallback != self._settings.nvidia_model else self._settings.nvidia_max_retries
        for attempt in range(retries + 1):
            state["backoff_failure"] = None
            started = perf_counter()
            record = dict(stage=stage, attempt=attempt + 1, requested_model=model,
                          returned_model=None, started_utc=datetime.now(timezone.utc).isoformat(),
                          parameters=dict(model=model, messages=messages, max_tokens=max_tokens,
                                          stream=False, **get_model_options(model)),
                          http_status=None, error_kind=None, backoff_seconds=0.0)
            # Request-scoped audit only; prompts/content must never enter ordinary logs.
            self.attempt_records.append(record)
            logger.info("NVIDIA NIM attempt started model=%s attempt=%s", model, attempt + 1)
            try:
                completion = await self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=max_tokens,
                    stream=False,
                    **get_model_options(model),
                )
            except OpenAIError as error:
                details = get_provider_error_details(
                    error, api_key=self._settings.nvidia_api_key.get_secret_value().strip())
                record.update(http_status=details.status_code, error_kind=details.kind.value,
                              request_seconds=perf_counter() - started)
                logger.error("NVIDIA NIM request failed model=%s attempt=%s duration_seconds=%.3f %s",
                             model, attempt + 1, perf_counter() - started, details.as_text())
                if details.kind in retryable and attempt < retries:
                    state["backoff_failure"] = details.kind
                    backoff_started = perf_counter()
                    try:
                        await asyncio.sleep(self._settings.nvidia_retry_backoff_seconds)
                    finally:
                        record["backoff_seconds"] = perf_counter() - backoff_started
                    continue
                raise NvidiaNimError("NVIDIA NIM isteği başarısız oldu.", kind=details.kind,
                                     status_code=details.status_code) from error
            except asyncio.CancelledError:
                record["error_kind"] = "cancelled"
                raise
            finally:
                record.update(seconds=perf_counter() - started,
                              finished_utc=datetime.now(timezone.utc).isoformat())
                record.setdefault("request_seconds", record["seconds"] - record["backoff_seconds"])
            record.update(http_status=200, returned_model=getattr(completion, "model", None))
            usage = getattr(completion, "usage", None)
            record["usage"] = usage.model_dump() if usage is not None and hasattr(usage, "model_dump") else None
            if not completion.choices:
                record["error_kind"] = ProviderErrorKind.INVALID_RESPONSE.value
                logger.warning("NVIDIA NIM empty response model=%s attempt=%s duration_seconds=%.3f",
                               model, attempt + 1, perf_counter() - started)
                raise NvidiaNimError("NVIDIA NIM boş bir yanıt döndürdü.",
                                     kind=ProviderErrorKind.INVALID_RESPONSE)
            finish = getattr(completion.choices[0], 'finish_reason', None)
            record.update(finish_reason=finish, response_content=completion.choices[0].message.content)
            usage = getattr(completion, 'usage', None)
            reasoning = getattr(getattr(usage, 'completion_tokens_details', None), 'reasoning_tokens', None)
            logger.info('NVIDIA response metadata model=%s output_limited=%s completion_tokens=%s '
                        'reasoning_tokens=%s duration_seconds=%.3f', model, finish == 'length',
                        getattr(usage, 'completion_tokens', None), reasoning, perf_counter() - started)
            if finish == 'length':
                record["error_kind"] = ProviderErrorKind.INVALID_RESPONSE.value
                failure('NVIDIA_OUTPUT_LIMIT')
                logger.warning('NVIDIA output truncated model=%s max_tokens=%s', model,
                               self._settings.nvidia_max_tokens if max_tokens is None else max_tokens)
                raise NvidiaNimError('NVIDIA yanıtı çıktı sınırında kesildi.', kind=ProviderErrorKind.INVALID_RESPONSE)
            content = completion.choices[0].message.content
            if not content or not content.strip():
                record["error_kind"] = ProviderErrorKind.INVALID_RESPONSE.value
                failure('NVIDIA_EMPTY_CONTENT')
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
