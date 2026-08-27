import re
from dataclasses import dataclass, field

from openpyxl.formula.tokenizer import Tokenizer, TokenizerError
from openpyxl.worksheet.worksheet import Worksheet

from app.services.provenance import (
    Provenance,
    build_provenance,
    evidence_from_reference,
)

CELL_REFERENCE_PATTERN = re.compile(
    r"^(?:(?:'[^']*(?:''[^']*)*'|[^'!]+)!)?"
    r"\$?[A-Z]{1,3}\$?\d+"
    r"(?::\$?[A-Z]{1,3}\$?\d+)?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FormulaAnalysis:
    cell: str
    formula: str
    references: list[str]
    cached_value: str | int | float | bool | None = None
    role: str = "calculation"
    provenance: Provenance | None = field(default=None, compare=False)


def analyze_formulas(
    worksheet: Worksheet,
    value_worksheet: Worksheet | None = None,
) -> list[FormulaAnalysis]:
    formulas: list[FormulaAnalysis] = []

    for cell in worksheet._cells.values():
        if cell.data_type != "f" or not isinstance(cell.value, str):
            continue

        cached_value = (
            _supported_value(value_worksheet[cell.coordinate].value)
            if value_worksheet is not None
            else None
        )
        formulas.append(
            FormulaAnalysis(
                cell=cell.coordinate,
                formula=cell.value,
                references=_extract_references(cell.value),
                cached_value=cached_value,
                role=_classify_formula(cell.value),
                provenance=build_provenance(
                    "formula_parser",
                    1.0,
                    (
                        evidence_from_reference(
                            worksheet.title,
                            cell.coordinate,
                            "워크북에서 직접 추출한 원본 수식",
                            value=cached_value,
                            formula=cell.value,
                        ),
                    ),
                ),
            )
        )

    return sorted(
        formulas,
        key=lambda formula: (
            worksheet[formula.cell].row,
            worksheet[formula.cell].column,
        ),
    )


def _extract_references(formula: str) -> list[str]:
    try:
        tokens = Tokenizer(formula).items
    except TokenizerError:
        return []

    references: list[str] = []
    seen: set[str] = set()

    for token in tokens:
        value = token.value
        if (
            token.type == "OPERAND"
            and token.subtype == "RANGE"
            and CELL_REFERENCE_PATTERN.fullmatch(value)
            and value not in seen
        ):
            references.append(value)
            seen.add(value)

    return references


def _classify_formula(formula: str) -> str:
    upper_formula = formula.upper()

    if "[" in formula or "_XLL." in upper_formula or "OFFICE.EXCEL.FUNCTIONS" in upper_formula:
        return "external"

    lookup_functions = (
        "VLOOKUP(",
        "HLOOKUP(",
        "XLOOKUP(",
        "LOOKUP(",
        "INDEX(",
        "MATCH(",
        "INDIRECT(",
        "OFFSET(",
    )
    if any(function in upper_formula for function in lookup_functions):
        return "lookup"

    presentation_functions = (
        "TEXT(",
        "UPPER(",
        "LOWER(",
        "PROPER(",
        "CONCAT(",
        "CONCATENATE(",
    )
    if any(function in upper_formula for function in presentation_functions) or "&" in formula:
        return "presentation"

    return "calculation"


def _supported_value(value: object) -> str | int | float | bool | None:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)
