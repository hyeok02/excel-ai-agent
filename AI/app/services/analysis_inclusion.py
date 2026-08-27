from dataclasses import dataclass
from enum import Enum

from app.services.provenance import Provenance


class AnalysisDecision(str, Enum):
    INCLUDE = "include"
    EXCLUDE = "exclude"


@dataclass(frozen=True)
class AnalysisInclusion:
    decision: AnalysisDecision
    reason_code: str
    reason: str
    provenance: Provenance | None = None

    def __post_init__(self) -> None:
        if not self.reason_code.strip():
            raise ValueError("reason_code는 비어 있을 수 없습니다.")
        if not self.reason.strip():
            raise ValueError("reason은 비어 있을 수 없습니다.")


INCLUDED_BUSINESS_WORKSHEET = AnalysisInclusion(
    decision=AnalysisDecision.INCLUDE,
    reason_code="business_worksheet",
    reason="사용자 업무 시트로 분석에 포함",
)

INCLUDED_POPULATED_REGION = AnalysisInclusion(
    decision=AnalysisDecision.INCLUDE,
    reason_code="populated_business_region",
    reason="업무 시트에서 값이 존재하는 영역으로 분석에 포함",
)
