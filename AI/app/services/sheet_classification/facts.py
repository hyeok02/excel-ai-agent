from dataclasses import dataclass
from numbers import Number

from openpyxl.worksheet.worksheet import Worksheet

from app.services.formula_analyzer import FormulaAnalysis


@dataclass(frozen=True)
class SheetFacts:
    populated_cells: list[object]
    formula_addresses: tuple[str, ...]
    text_cells: list[object]
    numeric_cells: list[object]
    narrative_cells: list[object]
    formula_ratio: float
    text_ratio: float


def extract_facts(
    worksheet: Worksheet,
    formulas: list[FormulaAnalysis],
) -> SheetFacts:
    populated = [cell for cell in worksheet._cells.values() if cell.value is not None]
    constants = [cell for cell in populated if cell.data_type != "f"]
    text_cells = [cell for cell in constants if isinstance(cell.value, str)]
    numeric_cells = [
        cell
        for cell in constants
        if isinstance(cell.value, Number) and not isinstance(cell.value, bool)
    ]
    narrative_cells = [
        cell
        for cell in text_cells
        if len(cell.value.strip()) >= 20 or "합니다" in cell.value or "하세요" in cell.value
    ]
    count = len(populated)
    return SheetFacts(
        populated_cells=populated,
        formula_addresses=tuple(
            f"{worksheet.title}!{formula.cell}" for formula in formulas[:5]
        ),
        text_cells=text_cells,
        numeric_cells=numeric_cells,
        narrative_cells=narrative_cells,
        formula_ratio=len(formulas) / count if count else 0,
        text_ratio=len(text_cells) / count if count else 0,
    )


def qualified_cells(worksheet: Worksheet, cells: list[object]) -> tuple[str, ...]:
    return tuple(
        f"{worksheet.title}!{getattr(cell, 'coordinate')}" for cell in cells[:5]
    )


def sample_populated_cells(worksheet: Worksheet) -> tuple[str, ...]:
    cells = [cell for cell in worksheet._cells.values() if cell.value is not None]
    return qualified_cells(worksheet, cells)
