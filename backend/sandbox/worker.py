"""Yalnızca izole Day 5 Docker image içinde çalıştırılan worker."""

import contextlib
import hashlib
import importlib.util
import io
import json
import math
import time
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
from backtesting import Backtest, Strategy

SCHEMA_VERSION = 1
INPUT_DIR = Path("/input")
OUTPUT_CAPTURE_LIMIT = 64 * 1024
REQUIRED_COLUMNS = ("Open", "High", "Low", "Close", "Volume")


class OutputLimitExceeded(RuntimeError):
    pass


class CappedTextSink(io.TextIOBase):
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._size = 0

    def write(self, value: str) -> int:
        encoded_size = len(value.encode("utf-8", errors="replace"))
        self._size += encoded_size
        if self._size > self._limit:
            raise OutputLimitExceeded
        return len(value)


def optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    converted = float(value)
    return converted if math.isfinite(converted) else None


def duration_string(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    duration = pd.Timedelta(value)
    return None if pd.isna(duration) else str(duration)


def metrics_from_stats(stats: Mapping[str, Any], initial_cash: float) -> dict[str, Any]:
    final_equity = optional_float(stats["Equity Final [$]"])
    return {
        "initial_cash": float(initial_cash),
        "final_equity": final_equity,
        "net_profit": (
            None if final_equity is None else final_equity - float(initial_cash)
        ),
        "return_percent": optional_float(stats["Return [%]"]),
        "buy_and_hold_return_percent": optional_float(
            stats["Buy & Hold Return [%]"]
        ),
        "number_of_trades": int(optional_float(stats["# Trades"]) or 0),
        "win_rate_percent": optional_float(stats["Win Rate [%]"]),
        "max_drawdown_percent": optional_float(stats["Max. Drawdown [%]"]),
        "sharpe_ratio": optional_float(stats["Sharpe Ratio"]),
        "sortino_ratio": optional_float(stats["Sortino Ratio"]),
        "profit_factor": optional_float(stats["Profit Factor"]),
        "best_trade_percent": optional_float(stats["Best Trade [%]"]),
        "worst_trade_percent": optional_float(stats["Worst Trade [%]"]),
        "average_trade_duration": duration_string(stats["Avg. Trade Duration"]),
        "exposure_time_percent": optional_float(stats["Exposure Time [%]"]),
    }


def emit(
    *,
    success: bool,
    stage: str,
    strategy_code_hash: str,
    started: float,
    error_code: str | None = None,
    error_message: str | None = None,
    metrics: dict[str, Any] | None = None,
) -> None:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "success": success,
        "stage": stage,
        "error_code": error_code,
        "error_message": error_message,
        "strategy_code_hash": strategy_code_hash,
        "metrics": metrics,
        "duration_seconds": max(0, time.monotonic() - started),
    }
    print(json.dumps(payload, allow_nan=False, separators=(",", ":")))


def load_request() -> dict[str, Any]:
    request = json.loads((INPUT_DIR / "request.json").read_text(encoding="utf-8"))
    if request.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("schema")
    if request.get("stage") not in {"smoke", "backtest"}:
        raise ValueError("stage")
    return request


def load_data() -> pd.DataFrame:
    data = pd.read_csv(INPUT_DIR / "data.csv", parse_dates=["Date"], index_col="Date")
    if data.empty or not set(REQUIRED_COLUMNS).issubset(data.columns):
        raise ValueError("data")
    return data.loc[:, list(REQUIRED_COLUMNS)]


def load_strategy(source_path: Path) -> type[Strategy]:
    spec = importlib.util.spec_from_file_location("generated_strategy", source_path)
    if spec is None or spec.loader is None:
        raise ImportError
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    strategy_class = getattr(module, "GeneratedStrategy", None)
    if strategy_class is None:
        raise LookupError("class")
    if not isinstance(strategy_class, type) or not issubclass(strategy_class, Strategy):
        raise TypeError("inheritance")
    if "init" not in strategy_class.__dict__ or "next" not in strategy_class.__dict__:
        raise TypeError("interface")
    return strategy_class


def main() -> None:
    started = time.monotonic()
    stage = "smoke"
    strategy_hash = "0" * 64
    try:
        request = load_request()
        stage = request["stage"]
        source_path = INPUT_DIR / "strategy.py"
        source_bytes = source_path.read_bytes()
        strategy_hash = hashlib.sha256(source_bytes).hexdigest()
        if strategy_hash != request.get("strategy_code_hash"):
            raise ValueError("hash")
        data = load_data()

        sink = CappedTextSink(OUTPUT_CAPTURE_LIMIT)
        try:
            with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
                strategy_class = load_strategy(source_path)
                backtest = Backtest(
                    data,
                    strategy_class,
                    cash=float(request["initial_cash"]),
                    commission=float(request["commission"]),
                    exclusive_orders=True,
                    trade_on_close=False,
                    finalize_trades=True,
                )
                stats = backtest.run()
        except OutputLimitExceeded:
            emit(
                success=False,
                stage=stage,
                strategy_code_hash=strategy_hash,
                started=started,
                error_code="STRATEGY_RESOURCE_LIMIT",
                error_message="Strateji izin verilen çıktı sınırını aştı.",
            )
            return
        except ImportError:
            emit(
                success=False,
                stage=stage,
                strategy_code_hash=strategy_hash,
                started=started,
                error_code="STRATEGY_IMPORT_ERROR",
                error_message="GeneratedStrategy modülü yüklenemedi.",
            )
            return
        except LookupError:
            emit(
                success=False,
                stage=stage,
                strategy_code_hash=strategy_hash,
                started=started,
                error_code="STRATEGY_CLASS_MISSING",
                error_message="GeneratedStrategy sınıfı yüklenemedi.",
            )
            return
        except TypeError:
            emit(
                success=False,
                stage=stage,
                strategy_code_hash=strategy_hash,
                started=started,
                error_code="STRATEGY_INTERFACE_ERROR",
                error_message="GeneratedStrategy arayüzü çalışma ortamıyla uyumsuz.",
            )
            return
        except BaseException:
            emit(
                success=False,
                stage=stage,
                strategy_code_hash=strategy_hash,
                started=started,
                error_code="STRATEGY_RUNTIME_ERROR",
                error_message="GeneratedStrategy izole backtest sırasında çalıştırılamadı.",
            )
            return

        emit(
            success=True,
            stage=stage,
            strategy_code_hash=strategy_hash,
            started=started,
            metrics=(
                metrics_from_stats(stats, float(request["initial_cash"]))
                if stage == "backtest"
                else None
            ),
        )
    except BaseException:
        emit(
            success=False,
            stage=stage,
            strategy_code_hash=strategy_hash,
            started=started,
            error_code="INVALID_SANDBOX_OUTPUT",
            error_message="Sandbox input sözleşmesi doğrulanamadı.",
        )


if __name__ == "__main__":
    main()
