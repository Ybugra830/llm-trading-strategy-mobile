"""Direct, bounded NVIDIA probes; no API server, market data, or sandbox."""

import argparse
import asyncio
import json
import logging
from time import perf_counter

import httpx
from openai import AsyncOpenAI, OpenAIError

from app.config import get_settings
from app.llm.nvidia_client import get_provider_error_details
from app.llm.nvidia_options import get_model_options


async def check_connection(timeout_seconds: float = 180) -> int:
    """Stop at the first failed probe, without retries or model fallback."""
    settings = get_settings()
    api_key = settings.nvidia_api_key.get_secret_value().strip()
    print(json.dumps({
        "model": settings.nvidia_model,
        "base_url": settings.nvidia_base_url,
        "api_key_present": bool(api_key),
        "application_timeout_seconds": settings.nvidia_request_timeout_seconds,
        "probe_timeout_seconds": timeout_seconds,
        "connect_timeout_seconds": 15,
        "write_timeout_seconds": 15,
        "pool_timeout_seconds": 15,
        "retries": 0,
        "fallback": False,
        "model_options": get_model_options(settings.nvidia_model),
    }), flush=True)
    if not api_key:
        print(json.dumps({"success": False, "failure_type": "missing_api_key"}))
        return 1

    async with AsyncOpenAI(
        api_key=api_key,
        base_url=settings.nvidia_base_url,
        timeout=httpx.Timeout(timeout_seconds, connect=15, write=15, pool=15),
        max_retries=0,
    ) as client:
        for name, prompt, max_tokens in (
            ("minimal", "Return exactly the word OK.", 32),
            ("code", "Write a minimal Python function that adds two numbers.", 512),
        ):
            started = perf_counter()
            record = {"probe": name, "requested_model": settings.nvidia_model,
                      "max_tokens": max_tokens, "stream": False}
            try:
                async with asyncio.timeout(timeout_seconds):
                    response = await client.chat.completions.with_raw_response.create(
                        model=settings.nvidia_model,
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=max_tokens,
                        stream=False,
                        **get_model_options(settings.nvidia_model),
                    )
                    completion = response.parse()
                content = (completion.choices[0].message.content or "").strip() if completion.choices else ""
                success = content == "OK" if name == "minimal" else bool(content)
                record.update(http_status=response.status_code, returned_model=completion.model,
                              success=success, failure_type=None if success else "unexpected_content",
                              finish_reason=completion.choices[0].finish_reason if completion.choices else None)
            except (OpenAIError, TimeoutError) as error:
                # Never serialize error bodies, request headers, or credentials.
                record.update(success=False, failure_type=type(error).__name__,
                              failure_category=get_provider_error_details(error).kind.value,
                              http_status=getattr(error, "status_code", None), returned_model=None)
            record["duration_seconds"] = round(perf_counter() - started, 3)
            print(json.dumps(record), flush=True)
            if not record["success"]:
                return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout-seconds", type=float, default=180)
    args = parser.parse_args()
    if not 5 <= args.timeout_seconds <= 300:
        parser.error("--timeout-seconds must be between 5 and 300")
    # SDK debug logs can contain raw requests; diagnostics print safe metadata only.
    for name in ("openai", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    return asyncio.run(check_connection(args.timeout_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
