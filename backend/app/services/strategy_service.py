"""Strateji üretim servisi."""

from app.llm.nvidia_client import NvidiaNimClient
from app.schemas.strategy import StrategyGenerateResponse


class StrategyService:
    """Strateji üretim akışını LLM istemcisine yönlendirir."""

    def __init__(self, client: NvidiaNimClient) -> None:
        self._client = client

    async def generate(self, prompt: str) -> StrategyGenerateResponse:
        """İstekten strateji kodu ve kullanılan model bilgisini üret."""
        code = await self._client.generate_code(prompt)
        return StrategyGenerateResponse(code=code, model=self._client.model)
