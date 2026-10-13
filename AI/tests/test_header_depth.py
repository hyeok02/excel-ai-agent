"""머리글이 바로 아래 데이터 블록 전체를 설명하는지."""
from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_headers import build_header_context, header_for

SHEET = "표"


def _row(number: int, values: dict[str, object]) -> IndexedRow:
    return IndexedRow(
        SHEET, number,
        tuple(
            IndexedCell(SHEET, f"{column}{number}", value, None)
            for column, value in values.items()
        ),
    )


def _table(header_row: int, data_rows: range) -> list[IndexedRow]:
    header = _row(header_row, {"A": "Date", "B": "Services", "C": "Creative"})
    return [header, *(_row(number, {"A": f"2020-{number:02d}", "B": number, "C": number})
                      for number in data_rows)]


def test_a_header_describes_the_whole_block_below_it() -> None:
    # 12행으로 끊으면 분기 20행짜리 표의 아래 8행이 머리글을 잃는다.
    rows = _table(1, range(2, 22))
    context = build_header_context(tuple(rows), rows)

    assert header_for(context, SHEET, 13, "B2") == "Services"
    assert header_for(context, SHEET, 21, "B2") == "Services"
    assert header_for(context, SHEET, 21, "C2") == "Creative"


def test_a_blank_row_ends_the_block() -> None:
    # 빈 줄 아래는 다른 표다. 위 머리글이 흘러들어오면 안 된다.
    rows = [*_table(1, range(2, 6)), _row(9, {"A": "2021-01", "B": 1, "C": 2})]
    context = build_header_context(tuple(rows), rows)

    assert header_for(context, SHEET, 5, "B2") == "Services"
    assert header_for(context, SHEET, 9, "B2") is None


def test_the_nearest_header_line_wins() -> None:
    rows = [
        _row(1, {"B": "Department", "C": "Department"}),
        _row(2, {"A": "Date", "B": "Services", "C": "Creative"}),
        _row(3, {"A": "2020-01", "B": 1, "C": 2}),
    ]
    context = build_header_context(tuple(rows), rows)

    assert header_for(context, SHEET, 3, "B2") == "Services"
    assert header_for(context, SHEET, 3, "A2") == "Date"
