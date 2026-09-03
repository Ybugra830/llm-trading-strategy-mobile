"""Opt-in deterministic real-Docker acceptance with production isolation flags."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import uuid

from app.config import get_settings
from app.runtime.docker_executor import DockerSandboxExecutor
from app.services.validation_service import ValidationService
from scripts.hardening_cases import CASES
from scripts.hardening_sources import SOURCES


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=Path('../reports/backend-hardening/deterministic.json'))
    args = parser.parse_args()
    executor = DockerSandboxExecutor(get_settings())
    for case, source in zip(CASES, SOURCES):
        result = ValidationService().validate(source, case.prompt)
        assert result.valid, result.errors
    with tempfile.TemporaryDirectory(prefix='trailing-contract-') as directory:
        folder = Path(directory).resolve()
        for case, source in zip(CASES, SOURCES):
            (folder / (case.name + '.py')).write_text(source, encoding='utf-8')
        (folder / 'behavior.py').write_bytes(Path(__file__).with_name('trailing_behavior_worker.py').read_bytes())
        command = executor._build_command(folder, 'trailing-contract-' + uuid.uuid4().hex)
        command[-1:-1] = ['--entrypoint=python']
        command.append('/input/behavior.py')
        completed = subprocess.run(command, capture_output=True, env=executor._safe_docker_environment(), timeout=60)
        if completed.returncode:
            # Only this repository-owned assertion harness runs here.
            raise RuntimeError(completed.stderr.decode('utf-8', errors='replace')[-4000:])
        report = json.loads(completed.stdout)
        assert report['worker_sha256'] == hashlib.sha256(Path('sandbox/worker.py').read_bytes()).hexdigest()
    invalid = 'from backtesting import Strategy\nclass GeneratedStrategy(Strategy):\n    def init(self):\n        pass\n    def next(self):\n        value = self.position.entry_price\n'
    smoke = executor.run_smoke(invalid, hashlib.sha256(invalid.encode()).hexdigest(), 10000, .0005)
    assert smoke.schema_version == 3 and not smoke.success
    assert smoke.safe_failure_type == 'AttributeError'
    assert smoke.safe_failure_context.family == 'position_management'
    assert smoke.safe_failure_context.api == 'Position.entry_price'
    report['position_error_protocol'] = smoke.model_dump(mode='json')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
