"""Strateji üretim endpoint'i testleri."""

import asyncio

import httpx

from app.api.strategy_routes import get_strategy_service
from app.llm.nvidia_client import NvidiaNimError
from app.main import app
from app.schemas.strategy import StrategyGenerateResponse


class SuccessfulStrategyService:
    """Ağ kullanmadan başarılı servis yanıtı üretir."""

    async def generate(self, prompt: str) -> StrategyGenerateResponse:
        return StrategyGenerateResponse(
            code="class GeneratedStrategy(Strategy):\n    pass",
            model="openai/gpt-oss-20b",
        )


class FailingStrategyService:
    """Sağlayıcı hatasını ağ kullanmadan taklit eder."""

    async def generate(self, prompt: str) -> StrategyGenerateResponse:
        raise NvidiaNimError("gizli sağlayıcı ayrıntısı")


def post_generate(payload: dict[str, str]) -> httpx.Response:
    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.post("/api/v1/strategies/generate", json=payload)

    return asyncio.run(send_request())


def test_generate_strategy_returns_code_and_model() -> None:
    app.dependency_overrides[get_strategy_service] = SuccessfulStrategyService
    try:
        response = post_generate({"prompt": "RSI düşükken al ve yüksekken sat."})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "code": "class GeneratedStrategy(Strategy):\n    pass",
        "model": "openai/gpt-oss-20b",
    }


def test_generate_strategy_rejects_too_short_prompt() -> None:
    app.dependency_overrides[get_strategy_service] = SuccessfulStrategyService
    try:
        response = post_generate({"prompt": "  dört  "})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422


def test_generate_strategy_converts_provider_failure_to_safe_error() -> None:
    app.dependency_overrides[get_strategy_service] = FailingStrategyService
    try:
        response = post_generate({"prompt": "Geçerli bir strateji isteği."})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json() == {"detail": "Strateji şu anda oluşturulamıyor."}
    assert "gizli sağlayıcı ayrıntısı" not in response.text
