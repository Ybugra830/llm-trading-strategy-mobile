"""Real Docker checks for bounded execution and safe runtime classification."""

import hashlib

from app.config import get_settings
from app.runtime.docker_executor import DockerSandboxExecutor
from app.runtime.models import SafeFailureType, SandboxErrorCode


TIMEOUT_STRATEGY = """\
from backtesting import Strategy


class GeneratedStrategy(Strategy):
    def init(self):
        pass

    def next(self):
        while True:
            pass
"""

ATTRIBUTE_ERROR_STRATEGY = """\
from backtesting import Strategy
import pandas as pd
from ta.trend import SMAIndicator


def broken_sma(values):
    return SMAIndicator(pd.Series(values), window=20).sma().to_numpy()


class GeneratedStrategy(Strategy):
    def init(self):
        self.sma = self.I(broken_sma, self.data.Close)

    def next(self):
        pass
"""


def run_smoke(executor: DockerSandboxExecutor, code: str):
    source = code.strip()
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    return executor.run_smoke(source, source_hash, 100_000, 0.002)


def main() -> int:
    settings = get_settings().model_copy(
        update={
            "sandbox_timeout_seconds": 1,
            "sandbox_startup_grace_seconds": 20,
        }
    )
    executor = DockerSandboxExecutor(settings)

    timeout = run_smoke(executor, TIMEOUT_STRATEGY)
    attribute = run_smoke(executor, ATTRIBUTE_ERROR_STRATEGY)

    print(
        "timeout "
        f"success={str(timeout.success).lower()} "
        f"error_code={timeout.error_code}"
    )
    print(
        "runtime "
        f"success={str(attribute.success).lower()} "
        f"error_code={attribute.error_code} "
        f"safe_failure_type={attribute.safe_failure_type}"
    )

    passed = (
        timeout.success is False
        and timeout.error_code == SandboxErrorCode.STRATEGY_TIMEOUT
        and attribute.success is False
        and attribute.error_code == SandboxErrorCode.STRATEGY_RUNTIME_ERROR
        and attribute.safe_failure_type == SafeFailureType.ATTRIBUTE_ERROR
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
