from collections import defaultdict
from dataclasses import dataclass
from enum import StrEnum
from numbers import Number

from openpyxl.workbook.workbook import Workbook
from openpyxl.worksheet.worksheet import Worksheet

from app.services.analysis_inclusion import AnalysisInclusion
from app.services.formula_analyzer import FormulaAnalysis


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
        if not self.code.strip():
            raise ValueError("시트 역할 판단 근거 코드는 비어 있을 수 없습니다.")
        if not self.message.strip():
            raise ValueError("시트 역할 판단 근거 설명은 비어 있을 수 없습니다.")
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
class _RoleSignal:
    role: SheetRole
    weight: int
    reason: SheetRoleReason


INPUT_NAME_KEYWORDS = (
    "input",
    "raw",
    "source",
    "data",
    "입력",
    "원본",
    "기초",
    "가정",
    "기준값",
)
CALCULATION_NAME_KEYWORDS = (
    "calc",
    "calculation",
    "model",
    "intermediate",
    "계산",
    "산출",
    "중간",
    "모델",
)
OUTPUT_NAME_KEYWORDS = (
    "output",
    "summary",
    "report",
    "dashboard",
    "result",
    "요약",
    "보고",
    "결과",
    "현황",
    "대시보드",
)
DOCUMENTATION_NAME_KEYWORDS = (
    "instruction",
    "guide",
    "readme",
    "help",
    "note",
    "안내",
    "설명",
    "도움말",
    "사용법",
    "주의사항",
)
SYSTEM_REASON_CODES = {
    "system_cache_worksheet",
    "addin_cache_worksheet",
}


def classify_sheets(
    workbook: Workbook,
    formulas_by_sheet: dict[str, list[FormulaAnalysis]],
    inclusions_by_sheet: dict[str, AnalysisInclusion],
) -> dict[str, SheetClassification]:
    """Classify every worksheet using structure, content and cross-sheet flow."""
    referenced_sheets: dict[str, set[str]] = defaultdict(set)
    referenced_by_sheets: dict[str, set[str]] = defaultdict(set)
    workbook_sheet_names = set(workbook.sheetnames)

    for sheet_name, formulas in formulas_by_sheet.items():
        for formula in formulas:
            for reference in formula.references:
                referenced_sheet = _reference_sheet_name(reference)
                if (
                    referenced_sheet is None
                    or referenced_sheet == sheet_name
                    or referenced_sheet not in workbook_sheet_names
                ):
                    continue
                referenced_sheets[sheet_name].add(referenced_sheet)
                referenced_by_sheets[referenced_sheet].add(sheet_name)

    return {
        worksheet.title: _classify_sheet(
            worksheet,
            formulas_by_sheet.get(worksheet.title, []),
            inclusions_by_sheet[worksheet.title],
            referenced_sheets[worksheet.title],
            referenced_by_sheets[worksheet.title],
        )
        for worksheet in workbook.worksheets
    }


def _classify_sheet(
    worksheet: Worksheet,
    formulas: list[FormulaAnalysis],
    inclusion: AnalysisInclusion,
    referenced_sheets: set[str],
    referenced_by_sheets: set[str],
) -> SheetClassification:
    if inclusion.reason_code in SYSTEM_REASON_CODES:
        return SheetClassification(
            role=SheetRole.SYSTEM,
            importance=SheetImportance.LOW,
            confidence=0.99,
            importance_score=0,
            reasons=(
                SheetRoleReason(
                    code="system_policy",
                    message=inclusion.reason,
                    evidence_cells=_sample_populated_cells(worksheet),
                ),
            ),
        )

    populated_cells = [
        cell for cell in worksheet._cells.values() if cell.value is not None
    ]
    formula_addresses = tuple(
        f"{worksheet.title}!{formula.cell}" for formula in formulas[:5]
    )
    constant_cells = [cell for cell in populated_cells if cell.data_type != "f"]
    text_cells = [cell for cell in constant_cells if isinstance(cell.value, str)]
    numeric_cells = [
        cell
        for cell in constant_cells
        if isinstance(cell.value, Number) and not isinstance(cell.value, bool)
    ]
    narrative_cells = [
        cell
        for cell in text_cells
        if len(cell.value.strip()) >= 20 or "합니다" in cell.value or "하세요" in cell.value
    ]
    populated_count = len(populated_cells)
    formula_ratio = len(formulas) / populated_count if populated_count else 0
    text_ratio = len(text_cells) / populated_count if populated_count else 0

    signals: list[_RoleSignal] = []
    normalized_name = worksheet.title.strip().casefold()
    _add_name_signal(signals, normalized_name, SheetRole.INPUT, INPUT_NAME_KEYWORDS)
    _add_name_signal(
        signals,
        normalized_name,
        SheetRole.CALCULATION,
        CALCULATION_NAME_KEYWORDS,
    )
    _add_name_signal(signals, normalized_name, SheetRole.OUTPUT, OUTPUT_NAME_KEYWORDS)
    _add_name_signal(
        signals,
        normalized_name,
        SheetRole.DOCUMENTATION,
        DOCUMENTATION_NAME_KEYWORDS,
    )

    if formulas:
        weight = 7 if formula_ratio >= 0.35 else 5 if formula_ratio >= 0.1 else 3
        signals.append(
            _RoleSignal(
                SheetRole.CALCULATION,
                weight,
                SheetRoleReason(
                    code="formula_density",
                    message=(
                        f"값이 있는 셀 {populated_count}개 중 수식 {len(formulas)}개"
                        f"({formula_ratio:.0%})가 계산 구조를 형성"
                    ),
                    evidence_cells=formula_addresses,
                ),
            )
        )

    if referenced_sheets and referenced_by_sheets:
        signals.append(
            _RoleSignal(
                SheetRole.CALCULATION,
                7,
                SheetRoleReason(
                    code="cross_sheet_intermediate",
                    message=(
                        f"{len(referenced_sheets)}개 시트를 참조하고 "
                        f"{len(referenced_by_sheets)}개 시트에서 다시 사용되는 중간 계산 시트"
                    ),
                    evidence_cells=formula_addresses,
                ),
            )
        )
    elif referenced_sheets:
        signals.append(
            _RoleSignal(
                SheetRole.OUTPUT,
                5,
                SheetRoleReason(
                    code="cross_sheet_consumer",
                    message=f"{len(referenced_sheets)}개 시트의 값을 가져와 결과를 구성",
                    evidence_cells=formula_addresses,
                ),
            )
        )

    if referenced_by_sheets:
        signals.append(
            _RoleSignal(
                SheetRole.INPUT,
                6,
                SheetRoleReason(
                    code="upstream_source",
                    message=f"{len(referenced_by_sheets)}개 시트가 이 시트의 값을 입력으로 사용",
                    evidence_cells=_sample_populated_cells(worksheet),
                ),
            )
        )

    chart_count = len(worksheet._charts)
    if chart_count:
        signals.append(
            _RoleSignal(
                SheetRole.OUTPUT,
                7,
                SheetRoleReason(
                    code="chart_presentation",
                    message=f"의사결정 결과를 보여주는 차트 {chart_count}개 포함",
                ),
            )
        )

    if not formulas and len(numeric_cells) >= 3:
        signals.append(
            _RoleSignal(
                SheetRole.INPUT,
                4,
                SheetRoleReason(
                    code="constant_data_source",
                    message=f"수식 없이 입력된 숫자 데이터 {len(numeric_cells)}개 포함",
                    evidence_cells=_qualified_cells(worksheet, numeric_cells),
                ),
            )
        )

    if (
        not formulas
        and text_ratio >= 0.7
        and len(numeric_cells) <= 2
        and (narrative_cells or populated_count <= 8)
    ):
        signals.append(
            _RoleSignal(
                SheetRole.DOCUMENTATION,
                6,
                SheetRoleReason(
                    code="narrative_content",
                    message=(
                        f"문자 셀 비율이 {text_ratio:.0%}이고 계산식이 없어 설명 중심 시트로 판단"
                    ),
                    evidence_cells=_qualified_cells(
                        worksheet,
                        narrative_cells or text_cells,
                    ),
                ),
            )
        )

    if not populated_cells:
        signals.append(
            _RoleSignal(
                SheetRole.DOCUMENTATION,
                2,
                SheetRoleReason(
                    code="empty_sheet",
                    message="값과 수식이 없어 업무 데이터보다 보조 시트에 가까움",
                ),
            )
        )

    scores = {role: 0 for role in SheetRole if role is not SheetRole.SYSTEM}
    for signal in signals:
        scores[signal.role] += signal.weight

    fallback_role = _fallback_role(formulas, numeric_cells, text_ratio)
    if max(scores.values(), default=0) == 0:
        scores[fallback_role] = 1
    ranked_roles = sorted(scores, key=lambda role: (-scores[role], role.value))
    selected_role = ranked_roles[0]
    selected_score = scores[selected_role]
    runner_up_score = scores[ranked_roles[1]] if len(ranked_roles) > 1 else 0
    selected_reasons = tuple(
        signal.reason for signal in signals if signal.role is selected_role
    )
    if not selected_reasons:
        selected_reasons = (
            SheetRoleReason(
                code="structural_fallback",
                message=_fallback_message(selected_role),
                evidence_cells=_sample_populated_cells(worksheet),
            ),
        )

    confidence = min(
        0.98,
        round(
            0.56
            + min(0.28, max(0, selected_score - runner_up_score) * 0.04)
            + min(0.12, selected_score * 0.01),
            2,
        ),
    )
    importance_score = _importance_score(
        selected_role,
        worksheet,
        formulas,
        referenced_sheets,
        referenced_by_sheets,
    )
    return SheetClassification(
        role=selected_role,
        importance=_importance_level(importance_score),
        confidence=confidence,
        importance_score=importance_score,
        reasons=selected_reasons[:4],
    )


def _add_name_signal(
    signals: list[_RoleSignal],
    normalized_name: str,
    role: SheetRole,
    keywords: tuple[str, ...],
) -> None:
    matched = next((keyword for keyword in keywords if keyword in normalized_name), None)
    if matched is None:
        return
    signals.append(
        _RoleSignal(
            role,
            8,
            SheetRoleReason(
                code=f"sheet_name_{role.value}",
                message=f"시트명 '{normalized_name}'에서 {role.value} 역할 단서 '{matched}' 탐지",
            ),
        )
    )


def _reference_sheet_name(reference: str) -> str | None:
    if "[" in reference or "!" not in reference:
        return None
    sheet_token, _ = reference.rsplit("!", 1)
    sheet_name = sheet_token.strip()
    if sheet_name.startswith("'") and sheet_name.endswith("'"):
        sheet_name = sheet_name[1:-1].replace("''", "'")
    return sheet_name


def _fallback_role(
    formulas: list[FormulaAnalysis],
    numeric_cells: list[object],
    text_ratio: float,
) -> SheetRole:
    if formulas:
        return SheetRole.CALCULATION
    if text_ratio >= 0.7 and len(numeric_cells) <= 2:
        return SheetRole.DOCUMENTATION
    return SheetRole.INPUT


def _fallback_message(role: SheetRole) -> str:
    return {
        SheetRole.INPUT: "상수형 업무 데이터가 중심이어서 입력 시트로 판단",
        SheetRole.CALCULATION: "수식 구조가 중심이어서 계산 시트로 판단",
        SheetRole.OUTPUT: "표현 요소와 결과 소비 구조를 기준으로 출력 시트로 판단",
        SheetRole.DOCUMENTATION: "문장형 텍스트가 중심이어서 설명 시트로 판단",
        SheetRole.SYSTEM: "시스템 정책에 따라 시스템 시트로 판단",
    }[role]


def _importance_score(
    role: SheetRole,
    worksheet: Worksheet,
    formulas: list[FormulaAnalysis],
    referenced_sheets: set[str],
    referenced_by_sheets: set[str],
) -> int:
    score = {
        SheetRole.INPUT: 30,
        SheetRole.CALCULATION: 35,
        SheetRole.OUTPUT: 45,
        SheetRole.DOCUMENTATION: 10,
        SheetRole.SYSTEM: 0,
    }[role]
    score += min(25, len(referenced_by_sheets) * 10)
    score += min(15, len(referenced_sheets) * 5)
    score += min(10, len(worksheet._charts) * 5)
    score += min(10, len(formulas) // 10 * 2)
    if worksheet.sheet_state == "visible" and role is not SheetRole.DOCUMENTATION:
        score += 5
    return min(100, score)


def _importance_level(score: int) -> SheetImportance:
    if score >= 80:
        return SheetImportance.CRITICAL
    if score >= 55:
        return SheetImportance.HIGH
    if score >= 25:
        return SheetImportance.MEDIUM
    return SheetImportance.LOW


def _qualified_cells(
    worksheet: Worksheet,
    cells: list[object],
) -> tuple[str, ...]:
    return tuple(
        f"{worksheet.title}!{getattr(cell, 'coordinate')}" for cell in cells[:5]
    )


def _sample_populated_cells(worksheet: Worksheet) -> tuple[str, ...]:
    cells = [cell for cell in worksheet._cells.values() if cell.value is not None]
    return _qualified_cells(worksheet, cells)
