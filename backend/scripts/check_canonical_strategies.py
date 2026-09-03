"""Validate and smoke-test all repository-owned canonical prompt examples."""

import hashlib
import json
import sys

from app.config import get_settings
from app.llm.prompt_examples import CANONICAL_STRATEGY_EXAMPLES
from app.runtime.docker_executor import DockerSandboxExecutor
from app.services.validation_service import ValidationService


def main() -> int:
    validator = ValidationService()
    sandbox = DockerSandboxExecutor(get_settings())
    rows = []
    for example in CANONICAL_STRATEGY_EXAMPLES:
        prepared = validator.prepare(example.source, example.english)
        smoke = None
        if prepared.validation.valid:
            code_hash = hashlib.sha256(prepared.code.encode("utf-8")).hexdigest()
            smoke = sandbox.run_smoke(prepared.code, code_hash, 100000, 0.002)
        row = {
            "family": example.family,
            "static_valid": prepared.validation.valid,
            "static_errors": prepared.validation.errors,
            "smoke_success": smoke.success if smoke is not None else False,
            "smoke_error_code": (
                smoke.error_code.value if smoke is not None and smoke.error_code else None
            ),
            "safe_failure_type": (
                smoke.safe_failure_type.value
                if smoke is not None and smoke.safe_failure_type
                else None
            ),
        }
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
    return 0 if all(row["static_valid"] and row["smoke_success"] for row in rows) else 1


if __name__ == "__main__":
    sys.exit(main())
