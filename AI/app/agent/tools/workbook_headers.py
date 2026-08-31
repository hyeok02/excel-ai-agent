import re
from collections import defaultdict
from dataclasses import replace

from app.agent.query.index import IndexedCell, IndexedRow
from app.services.provenance import AnalysisEvidence

HeaderContext = dict[tuple[str, int, str], str]
HEADER_LOOKBACK_ROWS = 12


def build_header_context(
    all_rows: tuple[IndexedRow, ...], selected_rows: list[IndexedRow]
) -> HeaderContext:
    candidates: dict[str, list[IndexedRow]] = defaultdict(list)
    for row in all_rows:
        if _is_header_row(row):
            candidates[row.sheet_name].append(row)
    context: HeaderContext = {}
    for row in selected_rows:
        preceding = [
            candidate
            for candidate in candidates[row.sheet_name]
            if 0 < row.row_number - candidate.row_number <= HEADER_LOOKBACK_ROWS
        ]
        for candidate in reversed(preceding):
            for cell in candidate.cells:
                if isinstance(cell.value, str) and cell.value.strip():
                    key = (row.sheet_name, row.row_number, _column(cell.address))
                    context.setdefault(key, cell.value.strip()[:120])
    return context


def header_for(
    context: HeaderContext, sheet_name: str, row_number: int, address: str
) -> str | None:
    return context.get((sheet_name, row_number, _column(address)))


def evidence_with_header(
    row: IndexedRow, cell: IndexedCell, context: HeaderContext
) -> AnalysisEvidence:
    evidence = cell.evidence()
    header = header_for(context, row.sheet_name, row.row_number, cell.address)
    return replace(evidence, description=header) if header else evidence


def _is_header_row(row: IndexedRow) -> bool:
    text_cells = [
        cell
        for cell in row.cells
        if isinstance(cell.value, str)
        and cell.value.strip()
        and not _looks_like_date(cell.value)
    ]
    return len(text_cells) >= 2 and len(text_cells) / len(row.cells) >= 0.5


def _looks_like_date(value: str) -> bool:
    return bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T.*)?", value.strip()))


def _column(address: str) -> str:
    match = re.match(r"[A-Z]+", address.upper())
    return match.group(0) if match else address
