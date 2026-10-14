"""점검표 모양의 작은 표. 목록·개수·조회 테스트가 함께 쓴다."""
from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_headers import build_header_context

SHEET = "작업현황"
HEADERS = {"C": "IP", "D": "장비", "E": "TCK 작업", "F": "네트워크 안정"}
MARKS = {6: "x", 7: "x", 8: "o", 9: "x", 10: "o", 11: "?", 12: None}


def row(number: int, values: dict[str, object]) -> IndexedRow:
    return IndexedRow(
        SHEET, number,
        tuple(
            IndexedCell(SHEET, f"{column}{number}", value, None)
            for column, value in values.items()
            if value is not None
        ),
    )


def rows() -> list[IndexedRow]:
    found = [row(5, HEADERS)]
    for number, mark in MARKS.items():
        found.append(row(number, {
            "C": f"10.1.7.{number}", "D": f"CVD #{number - 5}",
            "E": "o", "F": mark,
        }))
    return found


def built(builder, question: str):
    found = rows()
    return builder(found, build_header_context(tuple(found), found), question)
