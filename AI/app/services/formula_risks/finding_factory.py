from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks.models import FormulaRiskFinding
from app.services.provenance import build_provenance, evidence_from_reference


def build_formula_finding(
    kind: str,
    severity: str,
    sheet_name: str,
    item: FormulaAnalysis,
    message: str,
    *,
    reference: str | None = None,
    function_name: str | None = None,
) -> FormulaRiskFinding:
    return _build(
        kind,
        severity,
        sheet_name,
        item.cell,
        message,
        item.formula,
        reference,
        function_name,
        None,
    )


def build_hardcoded_finding(
    sheet_name: str,
    cell: str,
    value: str | int | float | bool,
    expected_formula: str,
) -> FormulaRiskFinding:
    return _build(
        "hardcoded_value",
        "warning",
        sheet_name,
        cell,
        "반복 수식 영역에서 이 셀만 값이 직접 입력되어 계산 누락 가능성이 있습니다.",
        expected_formula,
        None,
        None,
        value,
    )


def _build(
    kind: str,
    severity: str,
    sheet_name: str,
    cell: str,
    message: str,
    formula: str,
    reference: str | None,
    function_name: str | None,
    observed_value: str | int | float | bool | None,
) -> FormulaRiskFinding:
    provenance = build_provenance(
        "formula_risk_detector",
        1.0,
        (
            evidence_from_reference(
                sheet_name,
                cell,
                "위험 판정에 사용한 원본 셀",
                value=observed_value,
                formula=formula or None,
            ),
        ),
    )
    return FormulaRiskFinding(
        kind=kind,
        severity=severity,
        sheet_name=sheet_name,
        cell=cell,
        message=message,
        formula=formula,
        reference=reference,
        function_name=function_name,
        observed_value=observed_value,
        provenance=provenance,
    )
