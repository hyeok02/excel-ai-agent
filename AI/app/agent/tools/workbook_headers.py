import re
from collections import defaultdict
from dataclasses import replace

from app.agent.query.index import IndexedCell, IndexedRow
from app.services.provenance import AnalysisEvidence

HeaderContext = dict[tuple[str, int, str], str]
HEADER_LOOKBACK_ROWS = 12
# 머리글이 설명할 수 있는 최대 깊이. 빈 줄을 만나면 그 전에 멈추므로
# 이 값은 끝없이 거슬러 올라가지 않게 막는 안전장치일 뿐이다.
MAX_HEADER_DISTANCE = 400


def build_header_context(
    all_rows: tuple[IndexedRow, ...], selected_rows: list[IndexedRow]
) -> HeaderContext:
    sheets: dict[str, dict[int, IndexedRow]] = defaultdict(dict)
    header_rows: dict[str, set[int]] = defaultdict(set)
    for row in all_rows:
        sheets[row.sheet_name][row.row_number] = row
        if _is_header_row(row):
            header_rows[row.sheet_name].add(row.row_number)
    context: HeaderContext = {}
    for row in selected_rows:
        for candidate in _governing_headers(
            sheets[row.sheet_name], header_rows[row.sheet_name], row.row_number
        ):
            for cell in candidate.cells:
                if isinstance(cell.value, str) and cell.value.strip():
                    key = (row.sheet_name, row.row_number, _column(cell.address))
                    context.setdefault(key, cell.value.strip()[:120])
    return context


def _governing_headers(
    rows: dict[int, IndexedRow], header_rows: set[int], row_number: int
) -> list[IndexedRow]:
    """
    머리글은 바로 아래 이어지는 데이터 블록 전체를 설명한다.

    12행으로 끊어 두면 분기 20행짜리 표의 아래 8행이 머리글을 잃는다. 실제로
    그 때문에 비교 구간이 2022년부터로 잘려, 2023년에 있던 최고점을 놓치고
    "가장 많이 감소한 부서"의 답이 달라졌다.

    빈 줄은 다른 블록의 시작이므로 거기서 멈춘다. 가까운 머리글부터 돌려주어
    여러 줄짜리 머리글에서 아래쪽 줄이 이기게 한다.
    """
    found: list[IndexedRow] = []
    current = row_number - 1
    while current > 0 and row_number - current <= MAX_HEADER_DISTANCE:
        row = rows.get(current)
        if row is None:
            break
        if current in header_rows:
            found.append(row)
        elif found:
            break
        current -= 1
    return found


def header_for(
    context: HeaderContext, sheet_name: str, row_number: int, address: str
) -> str | None:
    return context.get((sheet_name, row_number, _column(address)))


def evidence_with_header(
    row: IndexedRow, cell: IndexedCell, context: HeaderContext
) -> AnalysisEvidence:
    evidence = cell.evidence()
    header = header_for(context, row.sheet_name, row.row_number, cell.address)
    if not header:
        return evidence
    format_hint = f" (Excel 표시 형식: {cell.number_format})" if "%" in cell.number_format else ""
    return replace(evidence, description=f"{header}{format_hint}")


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
