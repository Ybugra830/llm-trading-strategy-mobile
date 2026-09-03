"""Strateji üretim servisi."""

from app.llm.nvidia_client import NvidiaNimClient
from app.llm.repair_context import RepairFailureContext
from app.schemas.strategy import StrategyGenerateResponse


class StrategyService:
    """Strateji üretim akışını LLM istemcisine yönlendirir."""

    def __init__(self, client: NvidiaNimClient) -> None:
        self._client = client

    async def generate(self, prompt: str) -> StrategyGenerateResponse:
        """İstekten strateji kodu ve kullanılan model bilgisini üret."""
        code = await self._client.generate_code(prompt)
        return StrategyGenerateResponse(code=code, model=self._client.model)

    async def repair(
        self,
        original_prompt: str,
        current_code: str,
        context: RepairFailureContext,
    ) -> StrategyGenerateResponse:
        """Mevcut kodu özgün niyeti ve güvenli bulguları koruyarak onart."""
        code = await self._client.repair_code(
            original_prompt,
            current_code,
            context,
        )
        return StrategyGenerateResponse(code=code, model=self._client.model)
