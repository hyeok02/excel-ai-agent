import os
from pathlib import Path
from typing import Protocol

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.execution.models import AgentExecution
from app.agent.insights.context import build_execution_insight_context
from app.agent.insights.prompts import SYSTEM_PROMPT, build_execution_insight_prompt
from app.services.insights.models import (
    InsightConfigurationError,
    InsightGenerationError,
    WorkbookInsightReport,
)


class AgentInsightGenerator(Protocol):
    async def generate(self, execution: AgentExecution) -> WorkbookInsightReport: ...


class LangChainAgentInsightGenerator:
    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "LangChainAgentInsightGenerator":
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
        model = os.getenv("OPENAI_AGENT_INSIGHT_MODEL", "gpt-4.1-mini")
        return cls(api_key, model, timeout)

    def _build_model(self):
        return ChatOpenAI(
            model=self._model,
            api_key=self._api_key,
            timeout=self._timeout_seconds,
            max_retries=1,
            max_completion_tokens=1800,
        ).with_structured_output(WorkbookInsightReport, method="json_schema")

    async def generate(self, execution: AgentExecution) -> WorkbookInsightReport:
        if execution.succeeded_step_count == 0:
            raise InsightGenerationError(
                "성공한 Agent Tool 결과가 없어 인사이트를 생성할 수 없습니다."
            )
        try:
            context = build_execution_insight_context(execution)
            result = await self._build_model().ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=build_execution_insight_prompt(context)),
                ]
            )
            return WorkbookInsightReport.model_validate(result)
        except InsightGenerationError:
            raise
        except Exception as exception:
            raise InsightGenerationError(
                "Agent 실행 결과에서 근거 기반 인사이트를 생성하지 못했습니다."
            ) from exception
