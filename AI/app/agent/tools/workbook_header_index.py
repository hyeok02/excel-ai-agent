"""Detect stable headers once for each contiguous source block."""
from collections import Counter, defaultdict
from dataclasses import dataclass

from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_header_rows import column_of, header_score, is_header_row

_column = column_of

@dataclass(frozen=True)
class HeaderIndex:
    """어느 줄이 머리글인지 한 번만 가려 둔다.

    한 질문에 머리글 계산이 세 번 넘게 돌고, 그때마다 워크북 전체를 다시
    훑었다. 1500행짜리 파일에서 그 한 번이 1.9초였다.
    """

    sheets: dict[str, dict[int, IndexedRow]]
    header_rows: dict[str, set[int]]


def detect_header_rows(all_rows: tuple[IndexedRow, ...]) -> HeaderIndex:
    sheets: dict[str, dict[int, IndexedRow]] = defaultdict(dict)
    column_values: dict[tuple[str, str], Counter] = defaultdict(Counter)
    for row in all_rows:
        sheets[row.sheet_name][row.row_number] = row
        for cell in row.cells:
            if isinstance(cell.value, str) and cell.value.strip():
                column_values[(row.sheet_name, _column(cell.address))][cell.value] += 1
    header_rows: dict[str, set[int]] = defaultdict(set)
    scores: dict[tuple[str, int], object] = {}
    anchors = {}
    for row in sorted(all_rows, key=lambda item: (item.sheet_name, item.row_number)):
        previous = sheets[row.sheet_name].get(row.row_number - 1)
        if previous is None:
            anchors.pop(row.sheet_name, None)
        below = sheets[row.sheet_name].get(row.row_number + 1)
        if is_header_row(
            row, column_values, _block_width(sheets, row), below, scores
        ):
            anchor = anchors.get(row.sheet_name)
            score = header_score(row, column_values)
            # Once a block has a header, varying uniqueness among its text
            # records must not promote an ordinary row into a new header.
            # In event logs this made one company's headline label the next
            # company's value. A stronger header (e.g. a second header band)
            # or a repeated source header is still allowed.
            if anchor and score and not score.beats(anchor[1]):
                if not _repeated_header(row, anchor[0]):
                    continue
            header_rows[row.sheet_name].add(row.row_number)
            anchors[row.sheet_name] = (row, score)
    return HeaderIndex(sheets, header_rows)


def _repeated_header(row: IndexedRow, anchor: IndexedRow) -> bool:
    labels = {column_of(cell.address): cell.value for cell in anchor.cells if isinstance(cell.value, str)}
    current = {column_of(cell.address): cell.value for cell in row.cells if isinstance(cell.value, str)}
    return bool(labels) and len(labels) == len(current) and labels == current


def _block_width(sheets: dict[str, dict[int, IndexedRow]], row: IndexedRow) -> int:
    """이 줄 주변 표가 쓰는 열 수. 머리글은 표만큼 넓어야 한다."""
    nearby = sheets[row.sheet_name]
    return max(
        (len(found.cells)
         for offset in range(-5, 6)
         if (found := nearby.get(row.row_number + offset)) is not None),
        default=len(row.cells),
    )
