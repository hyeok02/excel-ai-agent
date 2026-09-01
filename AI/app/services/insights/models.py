from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from app.services.analysis_strategy import AnalysisDepth
from app.services.workbook_parser import WorkbookSummary


class WorkbookInsight(BaseModel):
    title: str = Field(description="워크북 또는 주요 시트의 업무 내용을 나타내는 짧은 제목")
    fact: str = Field(
        description="대상, 기준 시점, 실제 수치와 비교를 포함한 의사결정용 사실"
    )
    cause: str | None = Field(
        default=None, description="근거로 직접 확인된 원인. 확인할 수 없으면 null"
    )
    impact: str | None = Field(
        default=None,
        description="근거에서 직접 이어지는 짧은 검토 포인트. 확인할 수 없으면 null",
    )
    category: Literal["summary", "structure", "formula", "risk"]
    severity: Literal["info", "warning", "critical"]
    evidence: list[str] = Field(min_length=1)
    recommendation: str | None = Field(
        default=None, description="확인된 위험에 대한 구체적 조치. 일반론이면 null"
    )
    confidence: float = Field(
        ge=0,
        le=1,
        description="제시한 사실과 영향이 제공된 근거로 뒷받침되는 정도",
    )


class WorkbookInsightReport(BaseModel):
    overview: str = Field(
        description="핵심 대상과 기준 시점, 대표 수치와 변화 방향을 설명하는 전체 요약"
    )
    insights: list[WorkbookInsight] = Field(
        min_length=1,
        max_length=5,
        description="현재 상태, 기간 변화, 구성, 거래와 위험에 관한 구체적 사실",
    )
    limitations: list[str] = Field(default_factory=list)


class InsightValidationStatus(StrEnum):
    VERIFIED = "verified"
    LIMITED = "limited"


class ValidatedWorkbookInsight(WorkbookInsight):
    validation_status: InsightValidationStatus
    validation_reasons: list[str] = Field(default_factory=list)


class InsightValidationSummary(BaseModel):
    generated_count: int = Field(ge=0)
    verified_count: int = Field(ge=0)
    limited_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    notices: list[str] = Field(default_factory=list)


class ValidatedWorkbookInsightReport(BaseModel):
    overview: str
    insights: list[ValidatedWorkbookInsight]
    limitations: list[str] = Field(default_factory=list)
    validation: InsightValidationSummary


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
