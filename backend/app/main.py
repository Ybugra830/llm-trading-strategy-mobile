"""FastAPI uygulamasının başlangıç noktası."""

from fastapi import FastAPI

from app.api.backtest_routes import router as backtest_router
from app.api.strategy_routes import router as strategy_router
from app.api.strategy_lab_routes import router as strategy_lab_router
from app.api.validation_routes import router as validation_router

app = FastAPI(
    title="LLM Trading Strategy API",
    version="0.1.0",
)

app.include_router(strategy_router)
app.include_router(validation_router)
app.include_router(backtest_router)
app.include_router(strategy_lab_router)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Uygulamanın çalıştığını doğrulayan sağlık kontrolü."""
    return {"status": "ok"}
