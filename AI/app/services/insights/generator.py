import os
from pathlib import Path

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from app.services.analysis_strategy import (
    AnalysisDepth,
    AnalysisProfile,
    STANDARD_PROFILE,
    select_analysis_profile,
)
from app.services.insights.models import (
    InsightConfigurationError,
    InsightGenerationError,
    WorkbookInsightReport,
)
from app.services.insights.prompts import SYSTEM_PROMPT, build_user_prompt
from app.services.workbook_parser import WorkbookSummary


class LangChainInsightGenerator:
    def __init__(
        self,
        api_key: str,
        timeout_seconds: float,
        reasoning_effort: str,
    ) -> None:
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._reasoning_effort = reasoning_effort

    @classmethod
    def from_environment(cls) -> "LangChainInsightGenerator":
        from app.services import insight_generator

        insight_generator.load_dotenv(Path(__file__).resolve().parents[3] / ".env")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "replace-with-your-api-key":
            raise InsightConfigurationError(
                "OPENAI_API_KEY가 설정되지 않았습니다. AI/.env 파일을 확인하세요."
            )
        try:
            timeout_seconds = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
        except ValueError as exception:
            raise InsightConfigurationError(
                "OPENAI_TIMEOUT_SECONDS는 숫자여야 합니다."
            ) from exception
        return cls(
            api_key,
            timeout_seconds,
            os.getenv("OPENAI_REASONING_EFFORT", "minimal"),
        )

    def _build_model(self, profile: AnalysisProfile):
        fallback_model = (
            os.getenv("OPENAI_MODEL", profile.default_model)
            if profile == STANDARD_PROFILE
            else profile.default_model
        )
        model_name = os.getenv(profile.model_env_name, fallback_model)
        options: dict[str, object] = {}
        if model_name.startswith(("gpt-5", "o")):
            options["reasoning_effort"] = self._reasoning_effort
        return ChatOpenAI(
            model=model_name,
            api_key=self._api_key,
            timeout=self._timeout_seconds,
            max_retries=1,
            max_completion_tokens=profile.max_completion_tokens,
            **options,
        ).with_structured_output(WorkbookInsightReport, method="json_schema")

    async def generate(
        self,
        summary: WorkbookSummary,
        depth: AnalysisDepth = AnalysisDepth.AUTO,
    ) -> WorkbookInsightReport:
        profile = select_analysis_profile(summary, depth)
        try:
            result = await self._build_model(profile).ainvoke(
                [
                    SystemMessage(content=SYSTEM_PROMPT),
                    HumanMessage(content=build_user_prompt(summary, profile)),
                ]
            )
            return WorkbookInsightReport.model_validate(result)
        except Exception as exception:
            raise InsightGenerationError(
                "AI 인사이트를 생성하지 못했습니다."
            ) from exception
