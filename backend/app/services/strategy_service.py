"""Strateji üretim servisi."""

from app.llm.nvidia_client import NvidiaNimClient
from app.llm.repair_context import RepairFailureContext
from app.schemas.strategy import StrategyGenerateResponse
from app.services.admission_service import StrategyAdmissionError, StrategyAdmissionService
from app.execution_trace import stage


class StrategyService:
    """Strateji üretim akışını LLM istemcisine yönlendirir."""

    def __init__(self, client: NvidiaNimClient) -> None:
        self._client = client
        self._admission = StrategyAdmissionService(client)
        self._approved = {}

    async def generate(self, prompt: str) -> StrategyGenerateResponse:
        """İstekten strateji kodu ve kullanılan model bilgisini üret."""
        approved = await self._admission.assess(prompt)
        self._approved[prompt] = approved
        stage('generation', 'generation')
        code = await self._client.generate_code(approved.generation_prompt)
        return StrategyGenerateResponse(code=code, model=self._client.model, admission=approved.summary)

    async def repair(
        self,
        original_prompt: str,
        current_code: str,
        context: RepairFailureContext,
    ) -> StrategyGenerateResponse:
        """Mevcut kodu özgün niyeti ve güvenli bulguları koruyarak onart."""
        approved = self._approved.get(original_prompt)
        if approved is None:
            raise StrategyAdmissionError("needs_clarification", "incomplete", ["entry_rule", "exit_rule"])
        stage('repair', 'repair')
        code = await self._client.repair_code(
            approved.generation_prompt,
            current_code,
            context,
        )
        return StrategyGenerateResponse(code=code, model=self._client.model, admission=approved.summary)
