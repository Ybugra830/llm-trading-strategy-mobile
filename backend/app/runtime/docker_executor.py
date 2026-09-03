"""Generated strategy kaynak kodunu güvenli Docker worker'ına aktarır."""

import json
import logging
import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path

import pandas as pd
from pydantic import ValidationError

from app.config import Settings
from app.runtime.errors import SandboxProtocolError, SandboxUnavailableError
from app.runtime.models import (
    SANDBOX_SCHEMA_VERSION,
    SandboxErrorCode,
    SandboxResult,
    SandboxStage,
)
from app.runtime.smoke_data import build_smoke_ohlcv

logger = logging.getLogger(__name__)

SAFE_DOCKER_ENV_KEYS = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "DOCKER_HOST",
    "DOCKER_CONTEXT",
    "DOCKER_TLS_VERIFY",
    "DOCKER_CERT_PATH",
)


class DockerSandboxExecutor:
    """Docker CLI üzerinden fail-closed sandbox çalıştırır."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def run_smoke(
        self,
        code: str,
        strategy_code_hash: str,
        initial_cash: float,
        commission: float,
    ) -> SandboxResult:
        return self._execute(
            code,
            strategy_code_hash,
            build_smoke_ohlcv(),
            initial_cash,
            commission,
            "smoke",
        )

    def run_backtest(
        self,
        code: str,
        strategy_code_hash: str,
        data: pd.DataFrame,
        initial_cash: float,
        commission: float,
    ) -> SandboxResult:
        return self._execute(
            code,
            strategy_code_hash,
            data,
            initial_cash,
            commission,
            "backtest",
        )

    def _execute(
        self,
        code: str,
        strategy_code_hash: str,
        data: pd.DataFrame,
        initial_cash: float,
        commission: float,
        stage: SandboxStage,
    ) -> SandboxResult:
        container_name = f"strategy-sandbox-{uuid.uuid4().hex}"
        started = time.monotonic()
        safe_env = self._safe_docker_environment()

        with tempfile.TemporaryDirectory(prefix="strategy-input-") as input_name:
            with tempfile.TemporaryDirectory(prefix="strategy-output-") as output_name:
                input_dir = Path(input_name).resolve()
                output_dir = Path(output_name).resolve()
                self._write_inputs(
                    input_dir,
                    code,
                    strategy_code_hash,
                    data,
                    initial_cash,
                    commission,
                    stage,
                )
                command = self._build_command(input_dir, container_name)
                stdout_path = output_dir / "stdout.bin"
                stderr_path = output_dir / "stderr.bin"

                try:
                    with stdout_path.open("wb") as stdout_file, stderr_path.open(
                        "wb"
                    ) as stderr_file:
                        process = subprocess.Popen(
                            command,
                            shell=False,
                            stdout=stdout_file,
                            stderr=stderr_file,
                            env=safe_env,
                        )
                        limit_result = self._wait_for_process(
                            process,
                            stdout_path,
                            stderr_path,
                            container_name,
                            safe_env,
                            stage,
                            strategy_code_hash,
                            started,
                        )
                except FileNotFoundError as exc:
                    logger.error("Sandbox unavailable error_type=%s", type(exc).__name__)
                    raise SandboxUnavailableError from exc
                except (OSError, subprocess.SubprocessError) as exc:
                    logger.error("Sandbox launch failed error_type=%s", type(exc).__name__)
                    raise SandboxUnavailableError from exc

                if limit_result is not None:
                    return limit_result

                stdout = stdout_path.read_bytes()
                stderr = stderr_path.read_bytes()
                if len(stdout) + len(stderr) > self._settings.sandbox_max_output_bytes:
                    return self._failure_result(
                        stage,
                        strategy_code_hash,
                        SandboxErrorCode.STRATEGY_RESOURCE_LIMIT,
                        "Strateji izin verilen çıktı sınırını aştı.",
                        started,
                    )
                if process.returncode != 0:
                    if process.returncode in {137, -9}:
                        return self._failure_result(
                            stage,
                            strategy_code_hash,
                            SandboxErrorCode.STRATEGY_RESOURCE_LIMIT,
                            "Strateji izin verilen kaynak sınırını aştı.",
                            started,
                        )
                    logger.error(
                        "Sandbox worker failed return_code=%s", process.returncode
                    )
                    raise SandboxUnavailableError

                return self._parse_result(stdout, stage, strategy_code_hash)

    def _build_command(self, input_dir: Path, container_name: str) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network=none",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            f"--memory={self._settings.sandbox_memory}",
            f"--cpus={self._settings.sandbox_cpus:g}",
            f"--pids-limit={self._settings.sandbox_pids_limit}",
            "--user=10001:10001",
            "--tmpfs=/tmp:rw,nosuid,nodev,size=32m",
            "--ipc=none",
            "--ulimit",
            "nofile=64:64",
            "--mount",
            f"type=bind,source={input_dir},target=/input,readonly",
            self._settings.sandbox_image,
        ]

    def _write_inputs(
        self,
        input_dir: Path,
        code: str,
        strategy_code_hash: str,
        data: pd.DataFrame,
        initial_cash: float,
        commission: float,
        stage: SandboxStage,
    ) -> None:
        strategy_path = input_dir / "strategy.py"
        data_path = input_dir / "data.csv"
        request_path = input_dir / "request.json"
        strategy_path.write_bytes(code.encode("utf-8"))
        data.to_csv(data_path, index_label="Date")
        payload = {
            "schema_version": SANDBOX_SCHEMA_VERSION,
            "stage": stage,
            "initial_cash": float(initial_cash),
            "commission": float(commission),
            "strategy_timeout_seconds": self._settings.sandbox_timeout_seconds,
            "strategy_code_hash": strategy_code_hash,
        }
        request_path.write_text(
            json.dumps(payload, allow_nan=False),
            encoding="utf-8",
        )
        input_dir.chmod(0o755)
        for path in (strategy_path, data_path, request_path):
            path.chmod(0o644)

    def _wait_for_process(
        self,
        process: subprocess.Popen,
        stdout_path: Path,
        stderr_path: Path,
        container_name: str,
        safe_env: dict[str, str],
        stage: SandboxStage,
        strategy_code_hash: str,
        started: float,
    ) -> SandboxResult | None:
        while process.poll() is None:
            elapsed = time.monotonic() - started
            output_size = self._file_size(stdout_path) + self._file_size(stderr_path)
            if output_size > self._settings.sandbox_max_output_bytes:
                self._force_remove(container_name, safe_env)
                self._wait_after_cleanup(process)
                return self._failure_result(
                    stage,
                    strategy_code_hash,
                    SandboxErrorCode.STRATEGY_RESOURCE_LIMIT,
                    "Strateji izin verilen çıktı sınırını aştı.",
                    started,
                )
            host_timeout = (
                self._settings.sandbox_timeout_seconds
                + self._settings.sandbox_startup_grace_seconds
            )
            if elapsed > host_timeout:
                self._force_remove(container_name, safe_env)
                self._wait_after_cleanup(process)
                return self._failure_result(
                    stage,
                    strategy_code_hash,
                    SandboxErrorCode.SANDBOX_UNAVAILABLE,
                    "Sandbox çalışma ortamı zamanında başlatılamadı.",
                    started,
                )
            time.sleep(0.02)
        return None

    @staticmethod
    def _wait_after_cleanup(process: subprocess.Popen) -> None:
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=1)

    @staticmethod
    def _file_size(path: Path) -> int:
        try:
            return path.stat().st_size
        except FileNotFoundError:
            return 0

    @staticmethod
    def _force_remove(container_name: str, safe_env: dict[str, str]) -> None:
        try:
            subprocess.run(
                ["docker", "rm", "--force", container_name],
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=safe_env,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            logger.warning("Sandbox cleanup could not be confirmed.")

    @staticmethod
    def _safe_docker_environment() -> dict[str, str]:
        return {
            key: value
            for key in SAFE_DOCKER_ENV_KEYS
            if (value := os.environ.get(key)) is not None
        }

    @staticmethod
    def _failure_result(
        stage: SandboxStage,
        strategy_code_hash: str,
        error_code: SandboxErrorCode,
        error_message: str,
        started: float,
    ) -> SandboxResult:
        return SandboxResult(
            schema_version=SANDBOX_SCHEMA_VERSION,
            success=False,
            stage=stage,
            error_code=error_code,
            error_message=error_message,
            safe_failure_type=None,
            strategy_code_hash=strategy_code_hash,
            metrics=None,
            duration_seconds=max(0, time.monotonic() - started),
        )

    @staticmethod
    def _parse_result(
        stdout: bytes,
        expected_stage: SandboxStage,
        expected_hash: str,
    ) -> SandboxResult:
        try:
            payload = json.loads(stdout.decode("utf-8"))
            result = SandboxResult.model_validate(payload)
        except (UnicodeDecodeError, json.JSONDecodeError, ValidationError) as exc:
            logger.error("Sandbox returned invalid protocol output.")
            raise SandboxProtocolError from exc
        if result.stage != expected_stage or result.strategy_code_hash != expected_hash:
            logger.error("Sandbox result identity mismatch.")
            raise SandboxProtocolError
        return result
