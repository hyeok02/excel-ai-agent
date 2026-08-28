from openpyxl.worksheet.worksheet import Worksheet

from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks.detector import detect_reference_risks
from app.services.formula_risks.hardcode_detector import detect_hardcoded_values
from app.services.formula_risks.impact_analyzer import add_impact_analysis
from app.services.formula_risks.models import FormulaRiskSummary
from app.services.formula_risks.pattern_detector import detect_pattern_mismatches


def detect_formula_risks(
    sheet_names: list[str],
    formulas_by_sheet: list[tuple[str, list[FormulaAnalysis]]],
    worksheets: list[Worksheet] | None = None,
) -> FormulaRiskSummary:
    findings = detect_reference_risks(sheet_names, formulas_by_sheet)
    findings.extend(detect_pattern_mismatches(formulas_by_sheet))
    if worksheets:
        findings.extend(detect_hardcoded_values(worksheets))
    enriched = add_impact_analysis(findings, formulas_by_sheet)
    return FormulaRiskSummary.from_findings(enriched)
