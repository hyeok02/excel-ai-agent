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


def test_a_row_of_marks_is_not_a_header() -> None:
    # o/x 만 적힌 점검표는 데이터 행도 전부 글자다. 글자 비율만 보면 바로 윗
    # 데이터 행이 머리글이 되어 'IP' 자리에 '10.1.7.70'이 붙었다.
    rows = [
        _row(5, {"C": "IP", "D": "장비", "E": "작업", "F": "네트워크"}),
        *(
            _row(number, {"C": f"10.1.7.{number}", "D": f"CVD #{number}",
                          "E": "o", "F": "x"})
            for number in range(6, 12)
        ),
    ]
    context = build_header_context(tuple(rows), rows)

    assert header_for(context, SHEET, 7, "C7") == "IP"
    assert header_for(context, SHEET, 11, "C11") == "IP"
    assert header_for(context, SHEET, 11, "F11") == "네트워크"


def test_a_sparse_row_inside_a_block_is_not_a_header() -> None:
    # 표가 4열을 쓰는데 2칸만 적힌 줄은 머리글이 아니라 띄엄띄엄한 데이터다.
    # 아래 행들이 머리글을 잃지 않아야 한다.
    rows = [
        _row(5, {"C": "IP", "D": "장비", "E": "작업", "F": "네트워크"}),
        *(
            _row(number, {"C": f"10.1.7.{number}", "D": f"CVD #{number}",
                          "E": "o", "F": "x"})
            for number in (6, 7)
        ),
        _row(8, {"C": "10.1.7.8", "D": "CVD #8"}),
        *(
            _row(number, {"C": f"10.1.7.{number}", "D": f"CVD #{number}",
                          "E": "o", "F": "x"})
            for number in (9, 10, 11)
        ),
    ]
    context = build_header_context(tuple(rows), rows)

    assert header_for(context, SHEET, 9, "C9") == "IP"
    assert header_for(context, SHEET, 11, "D11") == "장비"
    assert header_for(context, SHEET, 11, "F11") == "네트워크"


def test_text_record_uniqueness_cannot_replace_the_column_headers() -> None:
    rows = [
        _row(30, {"H": "Company", "I": "Event Date", "J": "Headline"}),
        _row(31, {"H": "Alpha", "I": "2026-01-01", "J": "Unique event"}),
        _row(32, {"H": "Beta", "I": "2026-01-02", "J": "Repeated event"}),
        _row(33, {"H": "Beta", "I": "2026-01-03", "J": "Repeated event"}),
        _row(34, {"H": "Gamma", "I": "2026-01-04", "J": "Target agreement"}),
    ]
    context = build_header_context(tuple(rows), rows)

    assert header_for(context, SHEET, 32, "J32") == "Headline"
    assert header_for(context, SHEET, 34, "H34") == "Company"
    assert header_for(context, SHEET, 34, "J34") == "Headline"
