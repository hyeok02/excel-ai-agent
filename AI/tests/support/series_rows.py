"""기간별 부서 인원 표. 시계열 질문 테스트가 함께 쓴다."""
from app.agent.query.index import IndexedCell, IndexedRow

SHEET = "Headcount"
DATES = {7: "2023-09-01", 8: "2024-09-01", 9: "2025-06-01"}
COLUMNS = {
    "B": "Date", "C": "Total Employees",
    "D": "Services", "E": "Research & Development",
}
VALUES = {
    7: {"C": 6101, "D": 1277, "E": 1400},
    8: {"C": 5800, "D": 1150, "E": 1600},
    9: {"C": 5417, "D": 1081, "E": 1816},
}


def row(number: int, values: dict[str, object]) -> IndexedRow:
    return IndexedRow(
        SHEET, number,
        tuple(
            IndexedCell(SHEET, f"{column}{number}", value, None)
            for column, value in values.items()
        ),
    )


def rows() -> tuple[IndexedRow, ...]:
    header = row(6, COLUMNS)
    body = [
        row(number, {"B": DATES[number], **VALUES[number]})
        for number in sorted(DATES)
    ]
    return (header, *body)
