import re

from app.agent.query.index import IndexedCell, WorkbookDataIndex
from app.agent.tools.workbook_search_terms import relevance, search_terms

MAX_CANDIDATE_CELLS = 240


def select_writeback_candidates(
    instruction: str, index: WorkbookDataIndex
) -> list[IndexedCell]:
    terms = search_terms(instruction)
    scored = [
        (relevance(row, terms), position)
        for position, row in enumerate(index.rows)
    ]
    anchors = [
        position
        for score, position in sorted(scored, key=lambda item: (-item[0], item[1]))
        if score > 0
    ][:12]
    direct_references = set(re.findall(r"\b[A-Za-z]{1,3}[1-9][0-9]{0,6}\b", instruction))
    mentioned_sheets = {
        row.sheet_name for row in index.rows if row.sheet_name.casefold() in instruction.casefold()
    }
    selected_positions = _neighbor_positions(index, anchors)
    cells = [
        cell
        for position in selected_positions
        for cell in index.rows[position].cells
    ]
    direct = [
        cell
        for row in index.rows
        for cell in row.cells
        if cell.address.upper() in {item.upper() for item in direct_references}
        and (not mentioned_sheets or cell.sheet_name in mentioned_sheets)
    ]
    if not cells:
        dense_rows = sorted(index.rows, key=lambda row: len(row.cells), reverse=True)[:40]
        cells = [cell for row in dense_rows for cell in row.cells]
    return list({cell.reference: cell for cell in [*direct, *cells]}.values())[
        :MAX_CANDIDATE_CELLS
    ]


def _neighbor_positions(index: WorkbookDataIndex, anchors: list[int]) -> list[int]:
    selected: set[int] = set()
    for anchor in anchors:
        sheet_name = index.rows[anchor].sheet_name
        for position in range(max(0, anchor - 4), min(len(index.rows), anchor + 10)):
            if index.rows[position].sheet_name == sheet_name:
                selected.add(position)
    return sorted(selected)
