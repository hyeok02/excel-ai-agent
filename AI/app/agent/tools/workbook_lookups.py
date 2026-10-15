"""조회·목록·개수를 만든다. 검색이 고른 시트에서 먼저, 안 되면 전체에서.

검색이 표가 있는 시트를 놓치는 일이 있다. 'CVD #1 IP가 뭐야?'가 TAG 목록
시트로 가서 아무 답도 못 낸 적이 있다. 그렇다고 늘 전체를 훑으면 질문마다
몇 초씩 더 걸린다. 먼저 좁게 보고, 빈손일 때만 넓힌다.
"""
from dataclasses import dataclass

from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_cell_lookups import build_cell_lookup
from app.agent.tools.workbook_headers import (
    HeaderContext,
    HeaderIndex,
    build_header_context,
    detect_header_rows,
)
from app.agent.tools.workbook_mark_peaks import build_mark_peak
from app.agent.tools.workbook_row_counts import build_row_count
from app.agent.tools.workbook_row_lists import build_row_list

KEYS = ("row_list", "cell_lookup", "row_count", "mark_peak")


@dataclass(frozen=True)
class LookupResult:
    """조회 결과와, 그 조회가 읽은 행. 근거를 모을 범위가 함께 와야 한다."""

    data: dict[str, object]
    rows: list[IndexedRow]
    headers: HeaderContext
    widened: bool = False

    @property
    def references(self) -> list[str]:
        """조회가 근거로 드는 셀. 검색 행 밖에 있어도 근거에 실어야 한다."""
        references: list[str] = []
        for key in KEYS:
            item = self.data.get(key)
            if not isinstance(item, dict):
                continue
            references.extend(_cell_values(item))
            for match in item.get("matches") or ():
                if isinstance(match, dict):
                    references.extend(_cell_values(match))
        return list(dict.fromkeys(references))


def build_lookups(
    rows: list[IndexedRow],
    headers: HeaderContext,
    all_rows: tuple[IndexedRow, ...],
    question: str,
    detected: HeaderIndex | None = None,
    intent=None,
) -> LookupResult:
    found = _built(rows, headers, question, intent)
    if any(found.values()) or len(all_rows) == len(rows):
        return LookupResult(found, rows, headers)
    return _widened(all_rows, question, detected, intent)


def _widened(
    all_rows: tuple[IndexedRow, ...], question: str, detected: HeaderIndex | None, intent=None
) -> LookupResult:
    """시트를 한 장씩 본다.

    워크북 전체를 한 덩어리로 보면 열 후보가 열두 시트에서 섞여, 정작 표가
    있는 시트가 상위 후보 밖으로 밀렸다. 'CVD #1 IP가 뭐야?'가 그렇게 답을
    잃었다. 시트마다 따로 보고 먼저 나오는 결과를 쓴다.
    """
    found = detected or detect_header_rows(all_rows)
    searched = {row.sheet_name for row in all_rows}
    empty = _built([], {}, question, intent)
    for sheet_name in sorted(searched):
        sheet_rows = [row for row in all_rows if row.sheet_name == sheet_name]
        sheet_headers = build_header_context(all_rows, sheet_rows, found)
        built = _built(sheet_rows, sheet_headers, question, intent)
        if any(built.values()):
            return LookupResult(built, sheet_rows, sheet_headers, True)
    return LookupResult(empty, [], {}, True)


def _built(rows, headers, question, intent=None) -> dict[str, object]:
    result = {
        "row_list": build_row_list(rows, headers, question),
        "cell_lookup": build_cell_lookup(rows, headers, question),
        "row_count": build_row_count(rows, headers, question),
        "mark_peak": build_mark_peak(rows, headers, question),
    }
    if intent is not None and intent.from_model:
        # A language classification is not a table boundary. The legacy count
        # counts nonempty strings, including headings and neighboring tables;
        # only the source-table executor may certify a scoped count/aggregate.
        result["row_count"] = None
        if intent.kind != "row_list":
            result["row_list"] = None
        if intent.kind != "cell_lookup":
            result["cell_lookup"] = None
        if intent.kind != "aggregation":
            result["mark_peak"] = None
    return result


def _cell_values(item: dict) -> list[str]:
    return [
        value for value in item.values() if isinstance(value, str) and "!" in value
    ]
