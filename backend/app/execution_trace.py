"""Dependency-free request diagnostics; no prompts or provider bodies."""

import hashlib
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from uuid import uuid4

COUNTERS = ('assessment', 'generation', 'repair', 'ast', 'smoke', 'download', 'clean', 'backtest')


def source_revision():
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted((root / 'app').rglob('*.py')) + [root / 'sandbox' / 'worker.py']:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


@dataclass
class ExecutionTrace:
    request_id: str = field(default_factory=lambda: uuid4().hex)
    stage: str = 'request'
    error_code: str | None = None
    counters: dict = field(default_factory=lambda: dict.fromkeys(COUNTERS, 0))


current_trace = ContextVar('strategy_execution_trace', default=None)


def stage(name, counter=None):
    trace = current_trace.get()
    if trace:
        trace.stage = name
        if counter:
            trace.counters[counter] += 1


def failure(code):
    trace = current_trace.get()
    if trace and not trace.error_code:
        trace.error_code = code
