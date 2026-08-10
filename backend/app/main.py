"""FastAPI uygulamasının başlangıç noktası."""

from fastapi import FastAPI

app = FastAPI(
    title="LLM Trading Strategy API",
    version="0.1.0",
)


@app.get("/health")
def health_check() -> dict[str, str]:
    """Uygulamanın çalıştığını doğrulayan sağlık kontrolü."""
    return {"status": "ok"}
