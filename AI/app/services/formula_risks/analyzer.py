from openpyxl.worksheet.worksheet import Worksheet

from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks.detector import detect_reference_risks
from app.services.formula_risks.error_values import detect_error_values
from app.services.formula_risks.hardcode_detector import detect_hardcoded_values
from app.services.formula_risks.impact_analyzer import add_impact_analysis
from app.services.formula_risks.models import FormulaRiskFinding, FormulaRiskSummary
from app.services.formula_risks.pattern_detector import detect_pattern_mismatches


def detect_formula_risks(
    sheet_names: list[str],
    formulas_by_sheet: list[tuple[str, list[FormulaAnalysis]]],
    worksheets: list[Worksheet] | None = None,
) -> FormulaRiskSummary:
    findings = detect_error_values(formulas_by_sheet)
    findings.extend(detect_reference_risks(sheet_names, formulas_by_sheet))
    findings.extend(detect_pattern_mismatches(formulas_by_sheet))
    if worksheets:
        findings.extend(detect_hardcoded_values(worksheets))
    enriched = add_impact_analysis(_deduplicated(findings), formulas_by_sheet)
    return FormulaRiskSummary.from_findings(enriched)


def _deduplicated(findings: list[FormulaRiskFinding]) -> list[FormulaRiskFinding]:
    """같은 셀에서 같은 이유로 두 번 잡히는 항목을 한 번만 남긴다.

    한 수식이 같은 외부 파일을 여러 범위로 참조하면 범위마다 한 건씩 쌓여,
    화면에는 같은 셀이 여러 줄로 반복해서 나온다.
    """
    seen: set[tuple] = set()
    unique: list[FormulaRiskFinding] = []
    for item in findings:
        key = (item.kind, item.sheet_name, item.cell, _identity(item), item.function_name)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _identity(item: FormulaRiskFinding) -> str | None:
    """같은 항목인지 가리는 기준. 외부 참조는 범위가 아니라 파일이 기준이다."""
    if item.kind != "external_reference" or not item.reference:
        return item.reference
    closing = item.reference.find("]")
    return item.reference[: closing + 1] if closing > 0 else item.reference
