"""Production Docker executor ile zararsız generated-strategy smoke kontrolü."""

import hashlib

from app.config import get_settings
from app.runtime.docker_executor import DockerSandboxExecutor
from app.runtime.errors import SandboxUnavailableError

SAMPLE_STRATEGY = """\
from backtesting import Strategy
from backtesting.lib import crossover


def sma(values, period):
    return values.rolling(period).mean()


class GeneratedStrategy(Strategy):
    def init(self):
        self.fast = self.I(sma, self.data.Close.s, 10)
        self.slow = self.I(sma, self.data.Close.s, 20)

    def next(self):
        if crossover(self.fast, self.slow) and not self.position:
            self.buy()
        elif crossover(self.slow, self.fast) and self.position:
            self.position.close()
"""


def main() -> int:
    code = SAMPLE_STRATEGY.strip()
    code_hash = hashlib.sha256(code.encode("utf-8")).hexdigest()
    try:
        result = DockerSandboxExecutor(get_settings()).run_smoke(
            code,
            code_hash,
            100_000,
            0.002,
        )
    except SandboxUnavailableError:
        print("sandbox_available=false")
        print("Güvenli strateji çalışma ortamı şu anda kullanılamıyor.")
        return 2
    print(f"schema_version={result.schema_version}")
    print(f"sandboxed=true stage={result.stage} success={str(result.success).lower()}")
    print(f"strategy_hash_matches={str(result.strategy_code_hash == code_hash).lower()}")
    if not result.success:
        print(f"error_code={result.error_code}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
