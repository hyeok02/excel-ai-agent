import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.agent.contracts import AgentToolMetadata
from app.agent.planning.context import build_planning_context
from app.agent.planning.drafts import AgentExecutionPlanDraft
from app.agent.planning.models import (
    AgentExecutionPlan,
    AgentPlanner,
    PlanGenerationError,
    PlannerConfigurationError,
)
from app.agent.planning.prompts import SYSTEM_PROMPT, build_planning_prompt
from app.agent.planning.validation import ensure_executable_plan
from app.services.workbook_parsing.models import WorkbookSummary


class LangChainAgentPlanner:
    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds

    @classmethod
    def from_environment(cls) -> "LangChainAgentPlanner":
        load_dotenv(Path(__file__).resolve().parents[3] / ".env")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "replace-with-your-api-key":
            raise PlannerConfigurationError(
                "OPENAI_API_KEY가 설정되지 않았습니다. AI/.env 파일을 확인하세요."
            )
        try:
            timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
        except ValueError as exception:
            raise PlannerConfigurationError(
                "OPENAI_TIMEOUT_SECONDS는 숫자여야 합니다."
            ) from exception
        return cls(
            api_key,
            os.getenv("OPENAI_PLANNER_MODEL", "gpt-4.1-mini"),
            timeout_seconds,
        )

    def _build_model(self):
        return ChatOpenAI(
            model=self._model,
            api_key=self._api_key,
            timeout=self._timeout_seconds,
            max_retries=1,
            max_completion_tokens=1800,
        ).with_structured_output(AgentExecutionPlanDraft, method="json_schema")

    async def create_plan(
        self,
        intent: str,
        summary: WorkbookSummary,
        tools: tuple[AgentToolMetadata, ...],
    ) -> AgentExecutionPlan:
        normalized_intent = intent.strip()
        if not normalized_intent:
            raise PlanGenerationError("분석 목적은 비어 있을 수 없습니다.")
        context = build_planning_context(summary, tools)
        try:
            result = await self._build_model().ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=build_planning_prompt(normalized_intent, context)),
                ]
            )
            draft = AgentExecutionPlanDraft.model_validate(result)
            return ensure_executable_plan(
                draft.to_execution_plan(normalized_intent), tools
            )
        except PlanGenerationError:
            raise
        except Exception as exception:
            raise PlanGenerationError(
                "실행 가능한 Excel 분석 계획을 생성하지 못했습니다."
            ) from exception


__all__ = ["AgentPlanner", "LangChainAgentPlanner"]
