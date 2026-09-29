"""계산 결과가 오류로 남아 있는 셀을 찾는다.

수식이 계산에 실패하면 Excel은 #N/A, #DIV/0! 같은 오류를 셀 값으로 남긴다.
수식 본문만 읽어서는 드러나지 않고, 그 셀을 참조하는 계산까지 함께 틀어지므로
수식 위험 가운데 가장 확실한 항목이다.
"""
from collections.abc import Iterable

from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks.finding_factory import build_formula_finding
from app.services.formula_risks.models import FormulaRiskFinding

ERROR_CAUSES = {
    "#DIV/0!": "0으로 나누고 있습니다.",
    "#N/A": "찾는 값이 없어 조회에 실패했습니다.",
    "#VALUE!": "인자의 자료형이 맞지 않습니다.",
    "#REF!": "삭제되거나 이동된 셀을 가리킵니다.",
    "#NAME?": "함수 이름이나 이름 정의를 알아볼 수 없습니다.",
    "#NUM!": "계산할 수 없는 수치입니다.",
    "#NULL!": "참조 범위가 서로 겹치지 않습니다.",
    "#SPILL!": "결과를 펼칠 자리가 막혀 있습니다.",
    "#CALC!": "계산 엔진이 결과를 만들지 못했습니다.",
}


def detect_error_values(
    formulas_by_sheet: Iterable[tuple[str, list[FormulaAnalysis]]],
) -> list[FormulaRiskFinding]:
    findings: list[FormulaRiskFinding] = []
    for sheet_name, formulas in formulas_by_sheet:
        for item in formulas:
            code = error_code(item.cached_value)
            if code is None:
                continue
            findings.append(
                build_formula_finding(
                    "cached_error",
                    "error",
                    sheet_name,
                    item,
                    f"이 수식의 계산 결과가 {code} 오류입니다. {ERROR_CAUSES[code]}",
                    reference=code,
                    observed_value=code,
                )
            )
    return findings


def error_code(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    code = value.strip().upper()
    return code if code in ERROR_CAUSES else None
