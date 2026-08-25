from openpyxl.worksheet.worksheet import Worksheet

from app.services.formula_analyzer import FormulaAnalysis
from app.services.sheet_classification.facts import SheetFacts, qualified_cells
from app.services.sheet_classification.models import RoleSignal, SheetRole, SheetRoleReason


def content_signals(
    worksheet: Worksheet,
    formulas: list[FormulaAnalysis],
    facts: SheetFacts,
) -> list[RoleSignal]:
    signals = []
    if not formulas and len(facts.numeric_cells) >= 3:
        signals.append(
            RoleSignal(
                SheetRole.INPUT,
                4,
                SheetRoleReason(
                    "constant_data_source",
                    f"수식 없이 입력된 숫자 데이터 {len(facts.numeric_cells)}개 포함",
                    qualified_cells(worksheet, facts.numeric_cells),
                ),
            )
        )
    is_documentation = (
        not formulas
        and facts.text_ratio >= 0.7
        and len(facts.numeric_cells) <= 2
        and (facts.narrative_cells or len(facts.populated_cells) <= 8)
    )
    if is_documentation:
        signals.append(
            RoleSignal(
                SheetRole.DOCUMENTATION,
                6,
                SheetRoleReason(
                    "narrative_content",
                    f"문자 셀 비율이 {facts.text_ratio:.0%}이고 계산식이 없어 설명 중심 시트로 판단",
                    qualified_cells(
                        worksheet, facts.narrative_cells or facts.text_cells
                    ),
                ),
            )
        )
    if not facts.populated_cells:
        signals.append(
            RoleSignal(
                SheetRole.DOCUMENTATION,
                2,
                SheetRoleReason(
                    "empty_sheet", "값과 수식이 없어 업무 데이터보다 보조 시트에 가까움"
                ),
            )
        )
    return signals
