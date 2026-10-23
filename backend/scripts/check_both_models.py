r"""Bounded, direct NVIDIA probes; no application retries or automatic fallback.

Run from backend: .\.venv\Scripts\python.exe scripts/check_both_models.py
Only allowlisted metadata is printed; provider content and errors stay private.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass, field
from time import perf_counter

import httpx
from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.config import Settings, get_settings
from app.llm.nvidia_client import ProviderErrorKind, get_provider_error_details
from app.llm.nvidia_options import get_model_options

MESSAGES = [
    {"role": "system", "content": "You are a tester."},
    {"role": "user", "content": "Reply exactly with the word OK."},
]
FINISH_REASONS = {"stop", "length", "tool_calls", "content_filter", "function_call"}
UNSUPPORTED_CODES = {"unsupported_parameter", "unsupported_value", "unsupported_params"}


@dataclass
class Attempt:
    max_tokens: int
    seconds: float = 0
    api_accessible: bool = False
    ok_verified: bool = False
    http_status: int | None = None
    finish_reason: str | None = None
    empty_content: bool = False
    error_kind: str | None = None
    unsupported_parameters: bool = False


@dataclass
class ModelResult:
    role: str
    model: str | None
    status: str = "tested"
    attempts: list[Attempt] = field(default_factory=list)
    extra_attempt_reason: str | None = None

    def summary(self):
        return {
            "role": self.role, "model": self.model, "status": self.status,
            "api_accessible": any(a.api_accessible for a in self.attempts),
            "ok_verified": any(a.ok_verified for a in self.attempts),
            "seconds": round(sum(a.seconds for a in self.attempts), 3),
            "extra_attempt": len(self.attempts) > 1,
            "extra_attempt_reason": self.extra_attempt_reason,
            "attempts": [asdict(a) for a in self.attempts],
        }


def unsupported_parameter(error: OpenAIError) -> bool:
    """Recognize explicit codes only; never infer a parameter error from any 400."""
    code = getattr(error, "code", None)
    if isinstance(code, str) and code in UNSUPPORTED_CODES:
        return True
    body = getattr(error, "body", None)
    if isinstance(body, dict):
        nested = body.get("error", body)
        nested_code = nested.get("code") if isinstance(nested, dict) else None
        return isinstance(nested_code, str) and nested_code in UNSUPPORTED_CODES
    return False


async def attempt(client, model: str, tokens: int, timeout: float, options: dict) -> Attempt:
    result = Attempt(max_tokens=tokens)
    started = perf_counter()
    try:
        async with asyncio.timeout(timeout):
            raw = await client.chat.completions.with_raw_response.create(
                model=model, messages=MESSAGES, max_tokens=tokens, stream=False, **options,
            )
            result.api_accessible = True
            result.http_status = raw.status_code
            completion = raw.parse()
        if completion.choices:
            choice = completion.choices[0]
            result.finish_reason = choice.finish_reason if choice.finish_reason in FINISH_REASONS else "unknown"
            content = choice.message.content
            result.empty_content = not content or not content.strip()
            result.ok_verified = bool(content and content.strip() == "OK")
        else:
            result.empty_content = True
            result.error_kind = ProviderErrorKind.INVALID_RESPONSE.value
    except (OpenAIError, TimeoutError) as error:
        details = get_provider_error_details(error)
        result.http_status = details.status_code
        result.error_kind = details.kind.value
        # An HTTP error proves endpoint reachability, not model completion access.
        result.unsupported_parameters = isinstance(error, OpenAIError) and unsupported_parameter(error)
    except (httpx.HTTPError, OSError) as error:
        result.error_kind = (ProviderErrorKind.TIMEOUT.value if isinstance(error, httpx.TimeoutException)
                             else ProviderErrorKind.NETWORK.value)
    except (ValueError, TypeError, AttributeError):
        result.error_kind = ProviderErrorKind.INVALID_RESPONSE.value
    finally:
        result.seconds = round(perf_counter() - started, 3)
    return result


async def probe(client, role: str, model: str | None, timeout: float) -> ModelResult:
    result = ModelResult(role=role, model=model)
    if not model:
        result.status = "not_configured"
        return result
    first = await attempt(client, model, 10, timeout, get_model_options(model))
    result.attempts.append(first)
    if first.unsupported_parameters:
        result.extra_attempt_reason = "explicit_unsupported_parameter_code; optional_profile_removed"
        result.attempts.append(await attempt(client, model, 512, timeout, {}))
    elif first.api_accessible and (first.empty_content or first.finish_reason == "length"):
        result.extra_attempt_reason = "empty_or_truncated_output; larger_bounded_token_budget"
        result.attempts.append(await attempt(client, model, 512, timeout, get_model_options(model)))
    return result


async def run(settings: Settings) -> list[ModelResult]:
    if not settings.nvidia_api_key.get_secret_value().strip():
        return [ModelResult(role=role, model=model, status="missing_NVIDIA_API_KEY")
                for role, model in [("primary", settings.nvidia_model), ("fallback", settings.nvidia_fallback_model)]]
    timeout = min(30, settings.nvidia_request_timeout_seconds)
    async with AsyncOpenAI(
        api_key=settings.nvidia_api_key.get_secret_value().strip(),
        base_url=settings.nvidia_base_url, max_retries=0, timeout=httpx.Timeout(timeout),
    ) as client:
        # Even equal model names are probed independently; never use app fallback.
        return list(await asyncio.gather(
            probe(client, "primary", settings.nvidia_model, timeout),
            probe(client, "fallback", settings.nvidia_fallback_model, timeout),
        ))


def main() -> int:
    # SDK transport logs may contain a secret-bearing configured URL. Suppress them.
    for name in ("httpx", "httpcore", "openai"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    try:
        results = asyncio.run(run(get_settings()))
    except ValidationError:
        print("Settings validation failed; check local configuration. Values hidden.")
        return 2
    except (OpenAIError, httpx.HTTPError, OSError, ValueError):
        print("Diagnostic client setup failed. Details hidden.")
        return 2
    print("role | model | API completion | exact OK | seconds | HTTP/error | extra attempt")
    if results[0].model and results[0].model == results[1].model:
        print("Fallback matches primary; there is no distinct backup model.")
    for result in results:
        row = result.summary()
        statuses = ",".join(f"{a.http_status or '-'} / {a.error_kind or '-'}" for a in result.attempts)
        print(f"{result.role} | {result.model or '(not configured)'} | {row['api_accessible']} | "
              f"{row['ok_verified']} | {row['seconds']} | {statuses or result.status} | {row['extra_attempt']}")
        print(json.dumps(row, ensure_ascii=True))
    print("This checks current API access and a simple reply only, not strategy quality. "
          "Empty/truncated output is not proof a model is DOWN. No automatic fallback was used.")
    return 0 if all(r.summary()["ok_verified"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
