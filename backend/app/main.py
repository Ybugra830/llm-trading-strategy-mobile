"""FastAPI uygulamasının başlangıç noktası."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.backtest_routes import router as backtest_router
from app.api.strategy_routes import router as strategy_router
from app.api.strategy_lab_routes import router as strategy_lab_router
from app.api.validation_routes import router as validation_router
from app.config import get_settings
import json
import logging
from app.execution_trace import ExecutionTrace, current_trace, source_revision

LOADED_SOURCE_REVISION = source_revision()

app = FastAPI(
    title="LLM Trading Strategy API",
    version="0.1.0",
)


@app.middleware('http')
async def execution_diagnostics(request, call_next):
    trace = ExecutionTrace()
    token = current_trace.set(trace)
    try:
        response = await call_next(request)
        if response.status_code >= 400 and trace.error_code is None:
            trace.error_code = 'REQUEST_VALIDATION' if trace.stage == 'request' else f'HTTP_{response.status_code}'
        response.headers['X-Source-Revision'] = LOADED_SOURCE_REVISION
        response.headers['X-Request-ID'] = trace.request_id
        response.headers['X-Strategy-Stage'] = trace.stage
        response.headers['X-Strategy-Counts'] = json.dumps(trace.counters, separators=(',', ':'))
        if trace.error_code:
            response.headers['X-Error-Code'] = trace.error_code
        logging.getLogger(__name__).info('Strategy request id=%s stage=%s status=%s error=%s counts=%s',
            trace.request_id, trace.stage, response.status_code, trace.error_code, trace.counters)
        return response
    finally:
        current_trace.reset(token)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(strategy_router)
app.include_router(validation_router)
app.include_router(backtest_router)
app.include_router(strategy_lab_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Uygulamanın çalıştığını doğrulayan sağlık kontrolü."""
    return {"status": "ok"}
