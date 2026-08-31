from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.agent import AgentExecution
from app.agent.insights import AgentInsightGenerator, LangChainAgentInsightGenerator
from app.services.insights.models import (
    InsightConfigurationError,
    InsightGenerationError,
    WorkbookInsightReport,
)

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


def get_agent_insight_generator() -> AgentInsightGenerator:
    try:
        return LangChainAgentInsightGenerator.from_environment()
    except InsightConfigurationError as exception:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exception),
        ) from exception


@router.post("/insights", response_model=WorkbookInsightReport)
async def generate_agent_insights(
    execution: AgentExecution,
    generator: Annotated[AgentInsightGenerator, Depends(get_agent_insight_generator)],
) -> WorkbookInsightReport:
    try:
        return await generator.generate(execution)
    except InsightGenerationError as exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exception),
        ) from exception
