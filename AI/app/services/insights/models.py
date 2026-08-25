from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.services.analysis_strategy import AnalysisDepth
from app.services.workbook_parser import WorkbookSummary


class WorkbookInsight(BaseModel):
    title: str = Field(description="인사이트의 짧은 제목")
    description: str = Field(description="워크북에서 확인된 내용과 의미")
    category: Literal["summary", "structure", "formula", "risk"]
    severity: Literal["info", "warning", "critical"]
    evidence: list[str] = Field(min_length=1)
    recommendation: str | None = None


class WorkbookInsightReport(BaseModel):
    overview: str = Field(description="워크북 구조에 대한 전체 요약")
    insights: list[WorkbookInsight] = Field(min_length=1, max_length=5)
    limitations: list[str] = Field(default_factory=list)


class InsightConfigurationError(RuntimeError):
    """Raised when the LLM configuration is missing or invalid."""


class InsightGenerationError(RuntimeError):
    """Raised when the LLM cannot generate a validated insight report."""


class InsightGenerator(Protocol):
    async def generate(
        self,
        summary: WorkbookSummary,
        depth: AnalysisDepth = AnalysisDepth.AUTO,
    ) -> WorkbookInsightReport:
        """Generate a structured report from parsed workbook metadata."""
