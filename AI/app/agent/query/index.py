from dataclasses import dataclass

from app.agent.query.cell_values import formula_text, safe_indexed_value
from app.services.provenance import AnalysisEvidence, EvidenceKind
from app.services.workbook_loading import close_workbook, load_workbook_pair

MAX_INDEXED_CELLS = 50_000
MAX_ROWS_PER_SHEET = 10_000


@dataclass(frozen=True)
class IndexedCell:
    sheet_name: str
    address: str
    value: str | int | float | bool | None
    formula: str | None
    value_type: str = "text"
    number_format: str = "General"

    @property
    def reference(self) -> str:
        return f"{self.sheet_name}!{self.address}"

    def evidence(self) -> AnalysisEvidence:
        format_hint = (
            f" (Excel 표시 형식: {self.number_format})"
            if "%" in self.number_format
            else ""
        )
        return AnalysisEvidence(
            kind=EvidenceKind.FORMULA if self.formula else EvidenceKind.CELL,
            sheet_name=self.sheet_name,
            reference=self.address,
            description=f"질문과 관련해 원본 Excel에서 조회한 셀{format_hint}",
            value=self.value,
            formula=self.formula,
        )


@dataclass(frozen=True)
class IndexedRow:
    sheet_name: str
    row_number: int
    cells: tuple[IndexedCell, ...]

    @property
    def search_text(self) -> str:
        return " ".join(str(cell.value or cell.formula or "") for cell in self.cells).casefold()


@dataclass(frozen=True)
class WorkbookDataIndex:
    filename: str
    rows: tuple[IndexedRow, ...]
    indexed_cell_count: int
    truncated: bool
    truncated_sheet_names: frozenset[str] = frozenset()

    def truncated_for(self, sheet_names: set[str], whole_workbook: bool = False) -> bool:
        if whole_workbook or not self.truncated_sheet_names:
            return self.truncated
        return bool(sheet_names & self.truncated_sheet_names)


def build_workbook_data_index(
    filename: str, content: bytes, included_sheets: set[str] | None = None
) -> WorkbookDataIndex:
    formulas, values = load_workbook_pair(content, read_only=True)
    rows: list[IndexedRow] = []
    cell_count = 0
    truncated_sheets: set[str] = set()
    selected_sheets = [
        sheet
        for sheet in formulas.worksheets
        if included_sheets is None or sheet.title in included_sheets
    ]
    try:
        for sheet_index, formula_sheet in enumerate(selected_sheets):
            value_sheet = values[formula_sheet.title]
            for row_number, (formula_row, value_row) in enumerate(
                zip(formula_sheet.iter_rows(), value_sheet.iter_rows()), start=1
            ):
                if row_number > MAX_ROWS_PER_SHEET:
                    truncated_sheets.add(formula_sheet.title)
                    break
                if cell_count >= MAX_INDEXED_CELLS:
                    truncated_sheets.update(
                        sheet.title for sheet in selected_sheets[sheet_index:]
                    )
                    break
                cells = _indexed_cells(formula_sheet.title, formula_row, value_row)
                if cells:
                    remaining = MAX_INDEXED_CELLS - cell_count
                    cells = cells[:remaining]
                    rows.append(IndexedRow(formula_sheet.title, row_number, tuple(cells)))
                    cell_count += len(cells)
            if cell_count >= MAX_INDEXED_CELLS:
                truncated_sheets.update(
                    sheet.title for sheet in selected_sheets[sheet_index:]
                )
                break
    finally:
        close_workbook(formulas)
        close_workbook(values)
    return WorkbookDataIndex(
        filename, tuple(rows), cell_count, bool(truncated_sheets),
        frozenset(truncated_sheets),
    )


def _indexed_cells(sheet_name: str, formula_row: tuple, value_row: tuple) -> list[IndexedCell]:
    cells = []
    for formula_cell, value_cell in zip(formula_row, value_row):
        raw = formula_cell.value
        cached = value_cell.value
        if raw is None and cached is None:
            continue
        formula = formula_text(raw)
        value = cached if formula else raw
        safe_value, value_type = safe_indexed_value(value, formula)
        cells.append(
            IndexedCell(
                sheet_name,
                formula_cell.coordinate,
                safe_value,
                formula,
                value_type,
                str(formula_cell.number_format or "General"),
            )
        )
    return cells
