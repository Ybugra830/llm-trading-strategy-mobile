"""Docker executor komut ve protokol güvenliği testleri."""

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.runtime.docker_executor import DockerSandboxExecutor
from app.runtime.errors import SandboxProtocolError, SandboxUnavailableError
from app.runtime.models import (
    SANDBOX_SCHEMA_VERSION,
    SafeFailureType,
    SandboxErrorCode,
    SandboxResult,
)
from sandbox.worker import safe_failure_type


def settings(**overrides) -> Settings:
    values = {
        "_env_file": None,
        "sandbox_image": "llm-strategy-sandbox:test",
        "sandbox_timeout_seconds": 10,
        "sandbox_memory": "256m",
        "sandbox_cpus": 1,
        "sandbox_pids_limit": 64,
        "sandbox_max_output_bytes": 1_048_576,
    }
    values.update(overrides)
    return Settings(**values)


class SuccessfulPopen:
    calls: list[tuple[list[str], dict]] = []
    schema_version = SANDBOX_SCHEMA_VERSION
    return_code = 0
    extra_output = b""

    def __init__(self, command, **kwargs) -> None:
        type(self).calls.append((command, kwargs))
        request = self._read_request(command)
        assert request["strategy_timeout_seconds"] == 10
        payload = {
            "schema_version": type(self).schema_version,
            "success": True,
            "stage": request["stage"],
            "error_code": None,
            "error_message": None,
            "safe_failure_type": None,
            "strategy_code_hash": request["strategy_code_hash"],
            "metrics": None,
            "duration_seconds": 0.01,
        }
        kwargs["stdout"].write(json.dumps(payload).encode() + type(self).extra_output)
        kwargs["stdout"].flush()
        self.returncode = type(self).return_code

    @staticmethod
    def _read_request(command: list[str]) -> dict:
        mount = command[command.index("--mount") + 1]
        source = mount.split("source=", 1)[1].split(",target=", 1)[0]
        source_path = Path(source)
        request = json.loads(
            (source_path / "request.json").read_text(encoding="utf-8")
        )
        assert hashlib.sha256(
            (source_path / "strategy.py").read_bytes()
        ).hexdigest() == request["strategy_code_hash"]
        return request

    def poll(self):
        return self.returncode


class HangingPopen:
    def __init__(self, command, **kwargs) -> None:
        self.returncode = None

    def poll(self):
        return None

    def wait(self, timeout=None):
        self.returncode = -9
        return self.returncode


@pytest.fixture(autouse=True)
def reset_fake_popen() -> None:
    SuccessfulPopen.calls = []
    SuccessfulPopen.schema_version = SANDBOX_SCHEMA_VERSION
    SuccessfulPopen.return_code = 0
    SuccessfulPopen.extra_output = b""


def test_docker_command_contains_all_isolation_controls(monkeypatch) -> None:
    secret = "nvapi-must-not-reach-docker"
    monkeypatch.setenv("NVIDIA_API_KEY", secret)
    monkeypatch.setattr("app.runtime.docker_executor.subprocess.Popen", SuccessfulPopen)
    code = "class GeneratedStrategy: pass"
    code_hash = hashlib.sha256(code.encode()).hexdigest()

    result = DockerSandboxExecutor(settings()).run_smoke(code, code_hash, 100_000, 0.002)

    command, kwargs = SuccessfulPopen.calls[0]
    assert result.success is True
    assert kwargs["shell"] is False
    assert "--network=none" in command
    assert "--read-only" in command
    assert "--cap-drop=ALL" in command
    assert "--security-opt=no-new-privileges:true" in command
    assert "--memory=256m" in command
    assert "--cpus=1" in command
    assert "--pids-limit=64" in command
    assert "--user=10001:10001" in command
    assert "--tmpfs=/tmp:rw,nosuid,nodev,size=32m" in command
    assert "--ipc=none" in command
    assert command[command.index("--ulimit") + 1] == "nofile=64:64"
    assert command.count("--mount") == 1
    assert "target=/input,readonly" in command[command.index("--mount") + 1]
    assert code not in command
    assert all(".env" not in argument for argument in command)
    assert all("docker.sock" not in argument for argument in command)
    assert secret not in repr(kwargs["env"])
    assert "NVIDIA_API_KEY" not in kwargs["env"]


def test_unknown_worker_schema_is_rejected(monkeypatch) -> None:
    SuccessfulPopen.schema_version = SANDBOX_SCHEMA_VERSION + 1
    monkeypatch.setattr("app.runtime.docker_executor.subprocess.Popen", SuccessfulPopen)
    code = "class GeneratedStrategy: pass"

    with pytest.raises(SandboxProtocolError):
        DockerSandboxExecutor(settings()).run_smoke(
            code,
            hashlib.sha256(code.encode()).hexdigest(),
            100_000,
            0.002,
        )


def test_nonzero_worker_exit_is_safe_infrastructure_error(monkeypatch) -> None:
    SuccessfulPopen.return_code = 125
    monkeypatch.setattr("app.runtime.docker_executor.subprocess.Popen", SuccessfulPopen)
    code = "class GeneratedStrategy: pass"

    with pytest.raises(SandboxUnavailableError):
        DockerSandboxExecutor(settings()).run_smoke(
            code,
            hashlib.sha256(code.encode()).hexdigest(),
            100_000,
            0.002,
        )


def test_output_over_limit_is_not_parsed(monkeypatch) -> None:
    SuccessfulPopen.extra_output = b"x" * 5_000
    monkeypatch.setattr("app.runtime.docker_executor.subprocess.Popen", SuccessfulPopen)
    code = "class GeneratedStrategy: pass"

    result = DockerSandboxExecutor(
        settings(sandbox_max_output_bytes=4_096)
    ).run_smoke(
        code,
        hashlib.sha256(code.encode()).hexdigest(),
        100_000,
        0.002,
    )

    assert result.success is False
    assert result.error_code == SandboxErrorCode.STRATEGY_RESOURCE_LIMIT


def test_host_timeout_cleans_container_and_returns_infrastructure_error(monkeypatch) -> None:
    cleanup_calls: list[list[str]] = []
    clock = iter([0.0, 3.0, 3.1])
    monkeypatch.setattr("app.runtime.docker_executor.subprocess.Popen", HangingPopen)
    monkeypatch.setattr(
        "app.runtime.docker_executor.subprocess.run",
        lambda command, **kwargs: cleanup_calls.append(command),
    )
    monkeypatch.setattr(
        "app.runtime.docker_executor.time.monotonic", lambda: next(clock)
    )
    monkeypatch.setattr("app.runtime.docker_executor.time.sleep", lambda value: None)
    code = "class GeneratedStrategy: pass"

    result = DockerSandboxExecutor(
        settings(sandbox_timeout_seconds=1, sandbox_startup_grace_seconds=1)
    ).run_smoke(
        code,
        hashlib.sha256(code.encode()).hexdigest(),
        100_000,
        0.002,
    )

    assert result.error_code == SandboxErrorCode.SANDBOX_UNAVAILABLE
    assert cleanup_calls[0][:3] == ["docker", "rm", "--force"]


def test_missing_docker_binary_fails_closed(monkeypatch, tmp_path) -> None:
    marker = tmp_path / "must-not-exist"
    code = f'open(r"{marker}", "w").write("unsafe")'

    def missing_binary(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr("app.runtime.docker_executor.subprocess.Popen", missing_binary)

    with pytest.raises(SandboxUnavailableError):
        DockerSandboxExecutor(settings()).run_smoke(
            code,
            hashlib.sha256(code.encode()).hexdigest(),
            100_000,
            0.002,
        )
    assert marker.exists() is False


def test_runtime_protocol_requires_allowlisted_safe_failure_type() -> None:
    with pytest.raises(ValidationError):
        SandboxResult(
            schema_version=SANDBOX_SCHEMA_VERSION,
            success=False,
            stage="smoke",
            error_code=SandboxErrorCode.STRATEGY_RUNTIME_ERROR,
            error_message="GeneratedStrategy çalıştırılamadı.",
            strategy_code_hash="a" * 64,
            duration_seconds=0.01,
        )


def test_worker_failure_type_allowlist_and_unknown_fallback() -> None:
    assert safe_failure_type(AttributeError("not persisted")) == "AttributeError"
    assert safe_failure_type(PermissionError("not persisted")) == "UnknownRuntimeError"

    outer = RuntimeError("outer")
    outer.__cause__ = ValueError("inner")
    assert safe_failure_type(outer) == "ValueError"

    result = SandboxResult(
        schema_version=SANDBOX_SCHEMA_VERSION,
        success=False,
        stage="smoke",
        error_code=SandboxErrorCode.STRATEGY_RUNTIME_ERROR,
        error_message="GeneratedStrategy çalıştırılamadı.",
        safe_failure_type=SafeFailureType.UNKNOWN_RUNTIME_ERROR,
        strategy_code_hash="a" * 64,
        duration_seconds=0.01,
    )
    assert result.safe_failure_type == SafeFailureType.UNKNOWN_RUNTIME_ERROR
