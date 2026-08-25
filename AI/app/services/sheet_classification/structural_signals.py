from openpyxl.worksheet.worksheet import Worksheet

from app.services.formula_analyzer import FormulaAnalysis
from app.services.sheet_classification.facts import SheetFacts, sample_populated_cells
from app.services.sheet_classification.keywords import NAME_KEYWORDS
from app.services.sheet_classification.models import RoleSignal, SheetRole, SheetRoleReason


def structural_signals(
    worksheet: Worksheet,
    formulas: list[FormulaAnalysis],
    facts: SheetFacts,
    referenced_sheets: set[str],
    referenced_by_sheets: set[str],
) -> list[RoleSignal]:
    signals = _name_signals(worksheet.title.strip().casefold())
    if formulas:
        weight = 7 if facts.formula_ratio >= 0.35 else 5 if facts.formula_ratio >= 0.1 else 3
        signals.append(
            RoleSignal(
                SheetRole.CALCULATION,
                weight,
                SheetRoleReason(
                    "formula_density",
                    f"값이 있는 셀 {len(facts.populated_cells)}개 중 수식 "
                    f"{len(formulas)}개({facts.formula_ratio:.0%})가 계산 구조를 형성",
                    facts.formula_addresses,
                ),
            )
        )
    signals.extend(
        _reference_signals(
            worksheet,
            facts.formula_addresses,
            referenced_sheets,
            referenced_by_sheets,
        )
    )
    if worksheet._charts:
        signals.append(
            RoleSignal(
                SheetRole.OUTPUT,
                7,
                SheetRoleReason(
                    "chart_presentation",
                    f"의사결정 결과를 보여주는 차트 {len(worksheet._charts)}개 포함",
                ),
            )
        )
    return signals


def _name_signals(normalized_name: str) -> list[RoleSignal]:
    signals = []
    for role, keywords in NAME_KEYWORDS.items():
        matched = next((item for item in keywords if item in normalized_name), None)
        if matched:
            signals.append(
                RoleSignal(
                    role,
                    8,
                    SheetRoleReason(
                        f"sheet_name_{role.value}",
                        f"시트명 '{normalized_name}'에서 {role.value} 역할 단서 '{matched}' 탐지",
                    ),
                )
            )
    return signals


def _reference_signals(
    worksheet: Worksheet,
    formula_cells: tuple[str, ...],
    referenced: set[str],
    referenced_by: set[str],
) -> list[RoleSignal]:
    signals = []
    if referenced and referenced_by:
        signals.append(
            RoleSignal(
                SheetRole.CALCULATION,
                7,
                SheetRoleReason(
                    "cross_sheet_intermediate",
                    f"{len(referenced)}개 시트를 참조하고 {len(referenced_by)}개 시트에서 "
                    "다시 사용되는 중간 계산 시트",
                    formula_cells,
                ),
            )
        )
    elif referenced:
        signals.append(
            RoleSignal(
                SheetRole.OUTPUT,
                5,
                SheetRoleReason(
                    "cross_sheet_consumer",
                    f"{len(referenced)}개 시트의 값을 가져와 결과를 구성",
                    formula_cells,
                ),
            )
        )
    if referenced_by:
        signals.append(
            RoleSignal(
                SheetRole.INPUT,
                6,
                SheetRoleReason(
                    "upstream_source",
                    f"{len(referenced_by)}개 시트가 이 시트의 값을 입력으로 사용",
                    sample_populated_cells(worksheet),
                ),
            )
        )
    return signals
