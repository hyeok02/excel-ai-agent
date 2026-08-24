from dataclasses import dataclass
from enum import StrEnum


class SemanticRole(StrEnum):
    TITLE = "title"
    DESCRIPTION = "description"
    UNIT = "unit"
    HEADER = "header"
    DATA = "data"
    FORMULA = "formula"
    NOTE = "note"
    TOTAL = "total"
    INPUT = "input"
    CALCULATION = "calculation"
    OUTPUT = "output"
    INSTRUCTION = "instruction"
    WARNING = "warning"
    SOURCE_NOTE = "source_note"
    RULE_NOTE = "rule_note"
    SYSTEM_CACHE = "system_cache"
    IGNORE = "ignore"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SemanticReason:
    code: str
    message: str
    evidence_cells: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("의미 역할 판단 근거 코드는 비어 있을 수 없습니다.")
        if not self.message.strip():
            raise ValueError("의미 역할 판단 근거 설명은 비어 있을 수 없습니다.")
        if any(not cell.strip() for cell in self.evidence_cells):
            raise ValueError("의미 역할 판단 근거 셀은 비어 있을 수 없습니다.")
        if len(self.evidence_cells) != len(set(self.evidence_cells)):
            raise ValueError("의미 역할 판단 근거 셀은 중복될 수 없습니다.")


@dataclass(frozen=True)
class SemanticClassification:
    role: SemanticRole
    confidence: float
    reasons: tuple[SemanticReason, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.role, SemanticRole):
            raise ValueError("정의되지 않은 의미 역할입니다.")
        if not 0 <= self.confidence <= 1:
            raise ValueError("의미 역할 신뢰도는 0 이상 1 이하여야 합니다.")
