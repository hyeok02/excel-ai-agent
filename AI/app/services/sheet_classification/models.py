from dataclasses import dataclass
from enum import StrEnum


class SheetRole(StrEnum):
    INPUT = "input"
    CALCULATION = "calculation"
    OUTPUT = "output"
    DOCUMENTATION = "documentation"
    SYSTEM = "system"


class SheetImportance(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class SheetRoleReason:
    code: str
    message: str
    evidence_cells: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.code.strip() or not self.message.strip():
            raise ValueError("시트 역할 판단 근거는 비어 있을 수 없습니다.")
        if any(not cell.strip() for cell in self.evidence_cells):
            raise ValueError("시트 역할 판단 근거 셀은 비어 있을 수 없습니다.")
        if len(self.evidence_cells) != len(set(self.evidence_cells)):
            raise ValueError("시트 역할 판단 근거 셀은 중복될 수 없습니다.")


@dataclass(frozen=True)
class SheetClassification:
    role: SheetRole
    importance: SheetImportance
    confidence: float
    importance_score: int
    reasons: tuple[SheetRoleReason, ...] = ()

    def __post_init__(self) -> None:
        if not 0 <= self.confidence <= 1:
            raise ValueError("시트 역할 신뢰도는 0 이상 1 이하여야 합니다.")
        if not 0 <= self.importance_score <= 100:
            raise ValueError("시트 중요도 점수는 0 이상 100 이하여야 합니다.")


@dataclass(frozen=True)
class RoleSignal:
    role: SheetRole
    weight: int
    reason: SheetRoleReason
