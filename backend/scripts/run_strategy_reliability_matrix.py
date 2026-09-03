"""Opt-in real NVIDIA + Docker + Yahoo Strategy Lab reliability matrix."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from app.api.strategy_lab_routes import get_strategy_lab_service
from app.config import get_settings
from app.llm.nvidia_client import NvidiaNimClient
from app.llm.repair_context import RepairFailureContext
from app.main import app
from app.market.yahoo_provider import YahooFinanceProvider
from app.runtime.docker_executor import DockerSandboxExecutor
from app.runtime.models import SandboxResult
from app.schemas.strategy import StrategyGenerateResponse
from app.schemas.validation import StrategyValidationResponse
from app.services.strategy_lab_observer import GenerationSource
from app.services.strategy_lab_service import StrategyLabService
from app.services.strategy_service import StrategyService
from app.services.validation_service import ValidationService


@dataclass(frozen=True)
class PromptCase:
    prompt_id: str
    language: str
    family: str
    prompt: str


PROMPT_CASES = (
    PromptCase(
        "en_rsi",
        "en",
        "RSI",
        "Buy when RSI is below 35 and close when RSI is above 70.",
    ),
    PromptCase(
        "en_sma",
        "en",
        "SMA",
        "Buy when SMA20 crosses above SMA50 and close when SMA20 crosses below SMA50.",
    ),
    PromptCase(
        "en_ema",
        "en",
        "EMA",
        "Buy when EMA10 crosses above EMA30 and close when it crosses below.",
    ),
    PromptCase(
        "en_macd",
        "en",
        "MACD",
        "Buy when MACD crosses above its signal line and close when it crosses below.",
    ),
    PromptCase(
        "en_bollinger_rsi",
        "en",
        "Bollinger Bands + RSI",
        "Buy when price closes below the lower Bollinger Band and RSI is below 35; close when price reaches the middle band.",
    ),
    PromptCase(
        "tr_rsi",
        "tr",
        "RSI",
        "RSI 35'in altına düştüğünde al, RSI 70'in üzerine çıktığında pozisyonu kapat.",
    ),
    PromptCase(
        "tr_sma",
        "tr",
        "SMA",
        "20 günlük SMA 50 günlük SMA'yı yukarı kestiğinde al, aşağı kestiğinde pozisyonu kapat.",
    ),
    PromptCase(
        "tr_ema",
        "tr",
        "EMA",
        "10 günlük EMA 30 günlük EMA'yı yukarı kestiğinde al, aşağı kestiğinde pozisyonu kapat.",
    ),
    PromptCase(
        "tr_macd",
        "tr",
        "MACD",
        "MACD sinyal çizgisini yukarı kestiğinde al, aşağı kestiğinde pozisyonu kapat.",
    ),
)


class ReliabilityObserver:
    def __init__(self) -> None:
        self.attempts: list[dict[str, Any]] = []
        self.repair_requests: list[dict[str, Any]] = []
        self.backtest: dict[str, Any] | None = None

    def on_generated(
        self,
        attempt: int,
        source: GenerationSource,
        generated: StrategyGenerateResponse,
    ) -> None:
        self.attempts.append(
            {
                "attempt": attempt,
                "source": source,
                "model": generated.model,
                "raw_code": generated.code,
                "raw_sha256": hashlib.sha256(
                    generated.code.encode("utf-8")
                ).hexdigest(),
                "validation": None,
                "smoke": None,
            }
        )

    def on_validation(
        self,
        attempt: int,
        code: str,
        validation: StrategyValidationResponse,
    ) -> None:
        current = self._attempt(attempt)
        current["cleaned_code"] = code
        current["cleaned_sha256"] = hashlib.sha256(code.encode("utf-8")).hexdigest()
        current["validation"] = validation.model_dump(mode="json")

    def on_smoke(self, attempt: int, result: SandboxResult) -> None:
        self._attempt(attempt)["smoke"] = result.model_dump(mode="json")

    def on_repair_requested(
        self,
        failed_attempt: int,
        next_attempt: int,
        context: RepairFailureContext,
    ) -> None:
        self.repair_requests.append(
            {
                "failed_attempt": failed_attempt,
                "next_attempt": next_attempt,
                "context": {
                    "stage": context.stage,
                    "failure_type": context.failure_type,
                    "indicator_families": list(context.indicator_families),
                    "safe_findings": list(context.safe_findings),
                    "compatibility_guidance": list(context.compatibility_guidance),
                },
            }
        )

    def on_backtest(self, result: SandboxResult) -> None:
        self.backtest = result.model_dump(mode="json")

    def _attempt(self, attempt: int) -> dict[str, Any]:
        return next(item for item in self.attempts if item["attempt"] == attempt)


def build_service(observer: ReliabilityObserver) -> StrategyLabService:
    settings = get_settings()
    return StrategyLabService(
        strategy_service=StrategyService(NvidiaNimClient(settings)),
        validation_service=ValidationService(),
        sandbox_executor=DockerSandboxExecutor(settings),
        market_provider=YahooFinanceProvider(),
        max_strategy_versions=settings.max_strategy_versions,
        observer=observer,
    )


def classify_failure(record: dict[str, Any]) -> str | None:
    if record["http_status"] == 200:
        return None
    detail = (record.get("final_detail") or "").casefold()
    if record["http_status"] == 502:
        return "market_data" if "piyasa" in detail else "provider"
    if record["http_status"] == 503:
        return "sandbox_infrastructure"
    if record["http_status"] == 422:
        if "gerçek test" in detail:
            return "held_out_runtime"
        attempts = record["attempts"]
        for attempt in attempts:
            validation = attempt.get("validation")
            if validation and not validation["valid"]:
                for field, category in (
                    ("syntax_valid", "syntax"),
                    ("imports_valid", "import"),
                    ("security_valid", "security"),
                    ("interface_valid", "interface"),
                    ("lookahead_valid", "lookahead"),
                ):
                    if not validation[field]:
                        return category
            smoke = attempt.get("smoke")
            if smoke and not smoke["success"]:
                failure_type = smoke.get("safe_failure_type")
                return f"smoke:{failure_type or smoke.get('error_code')}"
        return "validation_unclassified"
    if record["http_status"] == 0:
        return "client_exception"
    return "unknown_http"


def persist_run(output_dir: Path, record: dict[str, Any]) -> None:
    stem = f"{record['prompt_id']}-run-{record['run_number']:02d}"
    run_dir = output_dir / "runs" / stem
    run_dir.mkdir(parents=True, exist_ok=True)
    for attempt in record["attempts"]:
        raw_code = attempt.pop("raw_code")
        raw_name = f"attempt-{attempt['attempt']:02d}-{attempt['source']}.py"
        (run_dir / raw_name).write_text(raw_code, encoding="utf-8")
        attempt["raw_code_file"] = raw_name
        cleaned = attempt.pop("cleaned_code", None)
        if cleaned is not None and cleaned != raw_code:
            cleaned_name = f"attempt-{attempt['attempt']:02d}-cleaned.py"
            (run_dir / cleaned_name).write_text(cleaned, encoding="utf-8")
            attempt["cleaned_code_file"] = cleaned_name
    (run_dir / "run.json").write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def aggregate(records: list[dict[str, Any]], runs_per_prompt: int) -> list[dict[str, Any]]:
    matrix = []
    minimum_first_pass = math.ceil(runs_per_prompt * 0.95)
    for case in PROMPT_CASES:
        selected = [item for item in records if item["prompt_id"] == case.prompt_id]
        if not selected:
            continue
        http_200 = sum(item["http_status"] == 200 for item in selected)
        first_pass = sum(item["first_pass"] for item in selected)
        unknown = sum(
            (item.get("failure_category") or "").startswith("unknown")
            or item.get("failure_category") == "validation_unclassified"
            for item in selected
        )
        repair_counts = [item["repair_count"] for item in selected]
        gate_passed = (
            len(selected) == runs_per_prompt
            and http_200 == runs_per_prompt
            and first_pass >= minimum_first_pass
            and unknown == 0
        )
        matrix.append(
            {
                "prompt_id": case.prompt_id,
                "language": case.language,
                "family": case.family,
                "runs": len(selected),
                "http_200": http_200,
                "first_pass": first_pass,
                "first_pass_percent": round(100 * first_pass / len(selected), 2),
                "repair_0": repair_counts.count(0),
                "repair_1": repair_counts.count(1),
                "repair_2": repair_counts.count(2),
                "average_repairs": round(sum(repair_counts) / len(selected), 3),
                "unknown_failures": unknown,
                "gate_passed": gate_passed,
            }
        )
    return matrix


def write_reports(
    output_dir: Path,
    records: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "summary.json").write_text(
        json.dumps({"runs": records, "matrix": matrix}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    run_fields = [
        "prompt_id", "language", "family", "run_number", "http_status",
        "attempt_count", "repair_count", "first_pass", "failure_category",
        "final_detail",
    ]
    with (output_dir / "summary.csv").open(
        "w", encoding="utf-8-sig", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=run_fields)
        writer.writeheader()
        writer.writerows({field: row.get(field) for field in run_fields} for row in records)
    lines = [
        "# Strategy Lab Reliability Matrix",
        "",
        "| Prompt | Lang | Family | HTTP 200 | First pass | Repairs 0/1/2 | Gate |",
        "|---|---|---|---:|---:|---:|---|",
    ]
    for row in matrix:
        lines.append(
            f"| {row['prompt_id']} | {row['language']} | {row['family']} | "
            f"{row['http_200']}/{row['runs']} | {row['first_pass']}/{row['runs']} "
            f"({row['first_pass_percent']}%) | {row['repair_0']}/"
            f"{row['repair_1']}/{row['repair_2']} | "
            f"{'PASS' if row['gate_passed'] else 'FAIL'} |"
        )
    (output_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


async def run_matrix(args: argparse.Namespace) -> int:
    cases = [case for case in PROMPT_CASES if not args.prompt_id or case.prompt_id in args.prompt_id]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output_dir = (
        Path(args.output_dir).resolve()
        if args.output_dir
        else Path(__file__).resolve().parents[2]
        / "reports"
        / "strategy-reliability"
        / timestamp
        / "post-hardening"
    )
    records: list[dict[str, Any]] = []
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://strategy-lab.local"
    ) as client:
        capabilities = await client.get("/api/v1/strategy-lab/capabilities")
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "capabilities.json").write_text(
            json.dumps(capabilities.json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        for case in cases:
            for run_number in range(1, args.runs_per_prompt + 1):
                observer = ReliabilityObserver()
                service = build_service(observer)
                app.dependency_overrides[get_strategy_lab_service] = lambda: service
                started = datetime.now(UTC)
                try:
                    response = await asyncio.wait_for(
                        client.post(
                            "/api/v1/strategy-lab/run",
                            json={
                                "prompt": case.prompt,
                                "symbol": args.symbol,
                                "initial_cash": args.initial_cash,
                                "commission": args.commission,
                            },
                            timeout=None,
                        ),
                        timeout=args.request_timeout_seconds,
                    )
                    try:
                        body = response.json()
                    except ValueError:
                        body = {}
                    detail = body.get("detail") if isinstance(body, dict) else None
                    status = response.status_code
                    response_status = body.get("status") if isinstance(body, dict) else None
                except Exception as error:
                    status = 0
                    response_status = None
                    detail = type(error).__name__
                finally:
                    app.dependency_overrides.clear()

                first = observer.attempts[0] if observer.attempts else None
                first_validation = first.get("validation") if first else None
                first_smoke = first.get("smoke") if first else None
                record = {
                    "prompt_id": case.prompt_id,
                    "language": case.language,
                    "family": case.family,
                    "prompt": case.prompt,
                    "run_number": run_number,
                    "started_at": started.isoformat(),
                    "completed_at": datetime.now(UTC).isoformat(),
                    "http_status": status,
                    "response_status": response_status,
                    "final_detail": detail if isinstance(detail, str) else None,
                    "attempt_count": len(observer.attempts),
                    "repair_count": len(observer.repair_requests),
                    "first_pass": bool(
                        len(observer.attempts) == 1
                        and first_validation
                        and first_validation["valid"]
                        and first_smoke
                        and first_smoke["success"]
                        and status == 200
                    ),
                    "attempts": observer.attempts,
                    "repair_requests": observer.repair_requests,
                    "backtest": observer.backtest,
                }
                record["failure_category"] = classify_failure(record)
                records.append(record)
                persist_run(output_dir, record)
                matrix = aggregate(records, args.runs_per_prompt)
                write_reports(output_dir, records, matrix)
                print(
                    json.dumps(
                        {
                            "progress": f"{case.prompt_id} {run_number}/{args.runs_per_prompt}",
                            "http_status": status,
                            "attempt_count": record["attempt_count"],
                            "repair_count": record["repair_count"],
                            "first_pass": record["first_pass"],
                            "failure_category": record["failure_category"],
                        },
                        ensure_ascii=False,
                    ),
                    flush=True,
                )

    matrix = aggregate(records, args.runs_per_prompt)
    write_reports(output_dir, records, matrix)
    passed = len(matrix) == len(cases) and all(row["gate_passed"] for row in matrix)
    print(f"REPORT_DIR={output_dir}", flush=True)
    print(f"GATE={'PASS' if passed else 'FAIL'}", flush=True)
    return 0 if passed else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-per-prompt", type=int, default=20)
    parser.add_argument(
        "--prompt-id",
        action="append",
        choices=[case.prompt_id for case in PROMPT_CASES],
    )
    parser.add_argument("--symbol", default="THYAO")
    parser.add_argument("--initial-cash", type=float, default=100000)
    parser.add_argument("--commission", type=float, default=0.002)
    parser.add_argument("--request-timeout-seconds", type=float, default=300)
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    if args.runs_per_prompt < 1:
        parser.error("--runs-per-prompt must be positive")
    if args.request_timeout_seconds <= 0:
        parser.error("--request-timeout-seconds must be positive")
    return args


if __name__ == "__main__":
    sys.exit(asyncio.run(run_matrix(parse_args())))
