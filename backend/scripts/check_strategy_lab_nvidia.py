"""Run the three requested NVIDIA + validation + Docker + Yahoo API checks."""

import argparse
import asyncio
import json
import logging
from contextlib import aclosing
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import httpx

from app.api.strategy_lab_routes import get_strategy_lab_service
from app.config import get_settings
from app.main import app
from scripts.run_strategy_reliability_matrix import ReliabilityObserver

PROMPTS = (
    ("rsi", "Buy when RSI is below 35 and close when RSI is above 70."),
    ("sma", "Buy when SMA20 crosses above SMA50 and close when SMA20 crosses below SMA50."),
    ("ema_rsi", "Buy when EMA20 is above EMA50 and RSI is below 40."),
)


class TimedObserver(ReliabilityObserver):
    def __init__(self):
        super().__init__()
        self.provider_started = perf_counter()

    def on_generated(self, attempt, source, generated):
        super().on_generated(attempt, source, generated)
        self.attempts[-1]["provider_duration_seconds"] = round(perf_counter() - self.provider_started, 3)

    def on_repair_requested(self, failed_attempt, next_attempt, context):
        super().on_repair_requested(failed_attempt, next_attempt, context)
        self.provider_started = perf_counter()


async def run_checks(output: Path) -> int:
    settings = get_settings()
    records = []
    output.parent.mkdir(parents=True, exist_ok=True)
    # Only a distinct, explicitly configured fallback can add a second budget.
    model_count = 2 if settings.nvidia_fallback_model and settings.nvidia_fallback_model != settings.nvidia_model else 1
    request_budget = (settings.nvidia_request_timeout_seconds * model_count * settings.max_strategy_versions
                      + (settings.sandbox_timeout_seconds + settings.sandbox_startup_grace_seconds) * 4 + 60)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strategy-lab.local") as client:
        for name, prompt in PROMPTS:
            started = perf_counter()
            observer = TimedObserver()

            async def observed_service():
                # Exercise the production dependency, adding only an observer.
                async with aclosing(get_strategy_lab_service()) as services:
                    async for service in services:
                        service._observer = observer
                        yield service

            app.dependency_overrides[get_strategy_lab_service] = observed_service
            body = {}
            status = None
            error_type = None
            print(json.dumps({"event": "started", "case": name, "model": settings.nvidia_model}), flush=True)
            try:
                async with asyncio.timeout(request_budget):
                    response = await client.post("/api/v1/strategy-lab/run", json={
                        "prompt": prompt, "symbol": "THYAO", "initial_cash": 100000, "commission": 0.002,
                    })
                status = response.status_code
                body = response.json()
            except Exception as error:
                error_type = type(error).__name__
            finally:
                app.dependency_overrides.pop(get_strategy_lab_service, None)
            runtime = body.get("runtime", {})
            validation = body.get("validation", {})
            record = {
                "case": name, "prompt": prompt, "requested_model": settings.nvidia_model,
                "duration_seconds": round(perf_counter() - started, 3),
                "http_status": status, "response_status": body.get("status"),
                "error_type": error_type,
                "safe_detail": body.get("detail"),
                "validation_valid": validation.get("valid"),
                "sandboxed": runtime.get("sandboxed"),
                "smoke_test_passed": runtime.get("smoke_test_passed"),
                "backtest_completed": bool(observer.backtest and observer.backtest.get("success")),
                "attempt_count": len(observer.attempts),
                "repair_count": len(observer.repair_requests),
                "attempts": [{"model": item["model"], "source": item["source"],
                              "provider_duration_seconds": item["provider_duration_seconds"],
                              "validation_valid": item["validation"].get("valid") if item["validation"] else None,
                              "smoke_success": item["smoke"].get("success") if item["smoke"] else None}
                             for item in observer.attempts],
            }
            record["passed"] = bool(
                status == 200 and record["response_status"] == "success"
                and record["validation_valid"] is True
                and record["sandboxed"] is True and record["smoke_test_passed"] is True
                and record["backtest_completed"] and record["attempt_count"] >= 1
            )
            records.append(record)
            output.write_text(json.dumps({"tested_at": datetime.now(UTC).isoformat(), "runs": records},
                                         indent=2), encoding="utf-8")
            print(json.dumps(record), flush=True)
    print(f"REPORT={output.resolve()}", flush=True)
    return 0 if all(record["passed"] for record in records) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("../reports/nvidia-provider/strategy-lab.json"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    for name in ("openai", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    return asyncio.run(run_checks(args.output))


if __name__ == "__main__":
    raise SystemExit(main())
