import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.writeback.models import WritebackProposalDraft
from app.agent.writeback.prompts import SYSTEM_PROMPT, build_writeback_prompt
from app.services.insights.models import InsightConfigurationError, InsightGenerationError

logger = logging.getLogger(__name__)


class LangChainWritebackGenerator:
    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "LangChainWritebackGenerator":
        load_dotenv(Path(__file__).resolve().parents[3] / ".env")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "replace-with-your-api-key":
            raise InsightConfigurationError(
                "OPENAI_API_KEY가 설정되지 않았습니다. AI/.env 파일을 확인하세요."
            )
        try:
            timeout = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
        except ValueError as exception:
            raise InsightConfigurationError(
                "OPENAI_TIMEOUT_SECONDS는 숫자여야 합니다."
            ) from exception
        return cls(
            api_key,
            os.getenv("OPENAI_WRITEBACK_MODEL", "gpt-4.1-2025-04-14"),
            timeout,
        )

    def _model_with_schema(self):
        return ChatOpenAI(
            model=self._model,
            api_key=self._api_key,
            timeout=self._timeout_seconds,
            max_retries=1,
            max_completion_tokens=1400,
        ).with_structured_output(WritebackProposalDraft, method="json_schema")

    async def generate(
        self, instruction: str, filename: str, context: dict[str, object]
    ) -> WritebackProposalDraft:
        try:
            result = await self._model_with_schema().ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(
                        content=build_writeback_prompt(instruction, filename, context)
                    ),
                ]
            )
            return WritebackProposalDraft.model_validate(result)
        except Exception as exception:
            logger.exception("Excel Write-back 모델 응답 생성 실패")
            raise InsightGenerationError("Excel 변경 제안을 생성하지 못했습니다.") from exception
