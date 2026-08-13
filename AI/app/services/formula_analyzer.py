import re
from dataclasses import dataclass

from openpyxl.formula.tokenizer import Tokenizer, TokenizerError
from openpyxl.worksheet.worksheet import Worksheet

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


def analyze_formulas(worksheet: Worksheet) -> list[FormulaAnalysis]:
    formulas: list[FormulaAnalysis] = []

    for row in worksheet.iter_rows():
        for cell in row:
            if cell.data_type != "f" or not isinstance(cell.value, str):
                continue

            formulas.append(
                FormulaAnalysis(
                    cell=cell.coordinate,
                    formula=cell.value,
                    references=_extract_references(cell.value),
                )
            )

    return formulas


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
