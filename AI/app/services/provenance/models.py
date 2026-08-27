from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias

EvidenceValue: TypeAlias = str | int | float | bool | None


class EvidenceKind(StrEnum):
    CELL = "cell"
    RANGE = "range"
    FORMULA = "formula"
    SHEET = "sheet"
    METADATA = "metadata"


class AnalysisMethod(StrEnum):
    RULE_BASED = "rule_based"
    DEPENDENCY_GRAPH = "dependency_graph"
    LLM = "llm"


@dataclass(frozen=True)
class AnalysisEvidence:
    kind: EvidenceKind
    sheet_name: str
    reference: str | None
    description: str
    value: EvidenceValue = None
    formula: str | None = None

    def __post_init__(self) -> None:
        if not self.sheet_name.strip():
            raise ValueError("근거 시트명은 비어 있을 수 없습니다.")
        if self.reference is not None and not self.reference.strip():
            raise ValueError("근거 셀 또는 범위는 비어 있을 수 없습니다.")
        if not self.description.strip():
            raise ValueError("근거 설명은 비어 있을 수 없습니다.")
        if self.kind is EvidenceKind.FORMULA and not self.formula:
            raise ValueError("수식 근거에는 원본 수식이 필요합니다.")


@dataclass(frozen=True)
class Provenance:
    analyzer: str
    method: AnalysisMethod
    confidence: float | None
    evidence: tuple[AnalysisEvidence, ...]

    def __post_init__(self) -> None:
        if not self.analyzer.strip():
            raise ValueError("근거 생성 분석기는 비어 있을 수 없습니다.")
        if self.confidence is not None and not 0 <= self.confidence <= 1:
            raise ValueError("근거 신뢰도는 0 이상 1 이하여야 합니다.")
        if not self.evidence:
            raise ValueError("Provenance에는 하나 이상의 근거가 필요합니다.")
