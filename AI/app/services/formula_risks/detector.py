from collections.abc import Iterable

from openpyxl.formula.tokenizer import Tokenizer, TokenizerError

from app.services.formula_analyzer import FormulaAnalysis
from app.services.formula_risks.models import FormulaRiskFinding, FormulaRiskSummary
from app.services.provenance import build_provenance, evidence_from_reference

DYNAMIC_FUNCTIONS = {"INDIRECT", "OFFSET"}


def detect_formula_risks(
    sheet_names: Iterable[str],
    formulas_by_sheet: Iterable[tuple[str, list[FormulaAnalysis]]],
) -> FormulaRiskSummary:
    known_sheets = {name.casefold() for name in sheet_names}
    findings: list[FormulaRiskFinding] = []
    for sheet_name, formulas in formulas_by_sheet:
        for item in formulas:
            findings.extend(_detect_formula(sheet_name, item, known_sheets))
    return FormulaRiskSummary.from_findings(findings)


def _detect_formula(
    sheet_name: str, item: FormulaAnalysis, known_sheets: set[str]
) -> list[FormulaRiskFinding]:
    findings: list[FormulaRiskFinding] = []
    if "#REF!" in item.formula.upper():
        findings.append(
            _finding(
                "broken_reference",
                "error",
                sheet_name,
                item,
                "삭제되거나 이동된 셀을 가리키는 깨진 참조가 있습니다.",
                reference="#REF!",
            )
        )
    try:
        tokens = Tokenizer(item.formula).items
    except TokenizerError:
        return findings
    seen: set[tuple[str, str]] = set()
    for token in tokens:
        if token.type == "FUNC" and token.subtype == "OPEN":
            function_name = token.value.rstrip("(").upper()
            if function_name in DYNAMIC_FUNCTIONS:
                key = ("dynamic_function", function_name)
                if key not in seen:
                    seen.add(key)
                    findings.append(_dynamic_finding(sheet_name, item, function_name))
        if token.type != "OPERAND" or token.subtype != "RANGE":
            continue
        reference = token.value
        if "[" in reference:
            key = ("external_reference", reference)
            if key not in seen:
                seen.add(key)
                findings.append(_external_finding(sheet_name, item, reference))
            continue
        referenced_sheet = _referenced_sheet(reference)
        if referenced_sheet and referenced_sheet.casefold() not in known_sheets:
            key = ("missing_sheet", referenced_sheet.casefold())
            if key not in seen:
                seen.add(key)
                findings.append(
                    _finding(
                        "missing_sheet",
                        "error",
                        sheet_name,
                        item,
                        f"존재하지 않는 '{referenced_sheet}' 시트를 참조합니다.",
                        reference=reference,
                    )
                )
    return findings


def _referenced_sheet(reference: str) -> str | None:
    if "!" not in reference:
        return None
    sheet_token = reference.rsplit("!", 1)[0]
    if sheet_token.startswith("'") and sheet_token.endswith("'"):
        return sheet_token[1:-1].replace("''", "'")
    return sheet_token


def _dynamic_finding(
    sheet_name: str, item: FormulaAnalysis, function_name: str
) -> FormulaRiskFinding:
    return _finding(
        "dynamic_function",
        "warning",
        sheet_name,
        item,
        f"{function_name} 함수는 실행 시점에 참조 위치가 달라져 영향 범위를 확정하기 어렵습니다.",
        function_name=function_name,
    )


def _external_finding(
    sheet_name: str, item: FormulaAnalysis, reference: str
) -> FormulaRiskFinding:
    return _finding(
        "external_reference",
        "warning",
        sheet_name,
        item,
        "다른 Excel 파일을 참조해 파일 이동이나 권한 변경 시 계산이 깨질 수 있습니다.",
        reference=reference,
    )


def _finding(
    kind: str,
    severity: str,
    sheet_name: str,
    item: FormulaAnalysis,
    message: str,
    *,
    reference: str | None = None,
    function_name: str | None = None,
) -> FormulaRiskFinding:
    provenance = build_provenance(
        "formula_risk_detector",
        1.0,
        (
            evidence_from_reference(
                sheet_name,
                item.cell,
                "위험 판정에 사용한 원본 수식",
                formula=item.formula,
            ),
        ),
    )
    return FormulaRiskFinding(
        kind,
        severity,
        sheet_name,
        item.cell,
        message,
        item.formula,
        reference,
        function_name,
        provenance,
    )
