from collections import Counter, defaultdict
from dataclasses import dataclass, replace

from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_header_rows import column_of, is_header_row
from app.services.provenance import AnalysisEvidence

HeaderContext = dict[tuple[str, int, str], str]
HEADER_LOOKBACK_ROWS = 12
# 머리글이 설명할 수 있는 최대 깊이. 빈 줄을 만나면 그 전에 멈추므로
# 이 값은 끝없이 거슬러 올라가지 않게 막는 안전장치일 뿐이다.
MAX_HEADER_DISTANCE = 400
# 머리글 위의 띠는 묶음 이름 한두 줄이다. '글자가 있으면 띠'로 두면 위쪽
# 모든 줄을 머리글 후보로 끌고 올라가, 행마다 백여 줄을 복사하게 된다.
MAX_BANNER_ROWS = 2


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
    for row in all_rows:
        below = sheets[row.sheet_name].get(row.row_number + 1)
        if is_header_row(
            row, column_values, _block_width(sheets, row), below, scores
        ):
            header_rows[row.sheet_name].add(row.row_number)
    return HeaderIndex(sheets, header_rows)


def build_header_context(
    all_rows: tuple[IndexedRow, ...],
    selected_rows: list[IndexedRow],
    detected: HeaderIndex | None = None,
) -> HeaderContext:
    found = detected or detect_header_rows(all_rows)
    context: HeaderContext = {}
    previous: dict[str, tuple[int, list[IndexedRow]]] = {}
    for row in sorted(selected_rows, key=lambda item: (item.sheet_name, item.row_number)):
        for candidate in _governing_for(found, previous, row):
            for cell in candidate.cells:
                if isinstance(cell.value, str) and cell.value.strip():
                    key = (row.sheet_name, row.row_number, _column(cell.address))
                    context.setdefault(key, cell.value.strip()[:120])
    return context


def _governing_for(found, previous, row) -> list[IndexedRow]:
    """바로 윗줄과 같은 블록이면 그 줄의 머리글을 그대로 쓴다.

    줄마다 최대 400행을 거슬러 올라가느라, 1400행짜리 워크북에서 머리글을
    붙이는 데만 1.9초가 걸렸다. 윗줄이 머리글이 아니고 빈 줄도 아니면 머리글은
    달라지지 않는다.
    """
    header_rows = found.header_rows[row.sheet_name]
    number = row.row_number
    seen = previous.get(row.sheet_name)
    if seen and seen[0] == number - 1 and number - 1 not in header_rows:
        previous[row.sheet_name] = (number, seen[1])
        return seen[1]
    governing = _governing_headers(found.sheets[row.sheet_name], header_rows, number)
    previous[row.sheet_name] = (number, governing)
    return governing


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
    banners = 0
    current = row_number - 1
    while current > 0 and row_number - current <= MAX_HEADER_DISTANCE:
        row = rows.get(current)
        if row is None:
            break
        if current in header_rows:
            found.append(row)
        elif found:
            # 머리글 바로 위의 좁은 띠(예: 여러 열을 묶는 '부서' 라벨)도
            # 머리글의 일부다. 폭이 좁아 단독으로는 머리글로 뽑히지 않는다.
            if banners >= MAX_BANNER_ROWS or not _is_banner_row(row):
                break
            banners += 1
            found.append(row)
        current -= 1
    return found


def _is_banner_row(row: IndexedRow) -> bool:
    return any(isinstance(cell.value, str) and cell.value.strip() for cell in row.cells)


def _block_width(sheets: dict[str, dict[int, IndexedRow]], row: IndexedRow) -> int:
    """이 줄 주변 표가 쓰는 열 수. 머리글은 표만큼 넓어야 한다."""
    nearby = sheets[row.sheet_name]
    return max(
        (len(found.cells)
         for offset in range(-5, 6)
         if (found := nearby.get(row.row_number + offset)) is not None),
        default=len(row.cells),
    )


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


def _column(address: str) -> str:
    return column_of(address)
