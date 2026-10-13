"""조건에 맞는 행을 코드가 직접 골라 나열하는지."""
from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.tools.workbook_headers import build_header_context
from app.agent.tools.workbook_row_lists import build_row_list

SHEET = "작업현황"
HEADERS = {"C": "IP", "D": "장비", "E": "TCK 작업", "F": "네트워크 안정"}
MARKS = {6: "x", 7: "x", 8: "o", 9: "x", 10: "o", 11: "?", 12: None}


def _row(number: int, values: dict[str, object]) -> IndexedRow:
    return IndexedRow(
        SHEET, number,
        tuple(
            IndexedCell(SHEET, f"{column}{number}", value, None)
            for column, value in values.items()
            if value is not None
        ),
    )


def _rows() -> list[IndexedRow]:
    rows = [_row(5, HEADERS)]
    for number, mark in MARKS.items():
        rows.append(_row(number, {
            "C": f"10.1.7.{number}", "D": f"CVD #{number - 5}",
            "E": "o", "F": mark,
        }))
    return rows


def _built(question: str):
    rows = _rows()
    return build_row_list(rows, build_header_context(tuple(rows), rows), question)


def test_lists_the_rows_marked_negative() -> None:
    found = _built("네트워크가 불안정한 장비는?")

    assert found["header"] == "네트워크 안정"
    assert found["label_header"] == "장비"
    assert found["polarity"] == "negative"
    assert [item["label"] for item in found["matches"]] == ["CVD #1", "CVD #2", "CVD #4"]
    assert found["blank_count"] == 1


def test_lists_the_rows_marked_positive() -> None:
    # '안정된'의 '안'이 부정으로 읽히면 안 된다. 머리글에 쓰인 말을 걷어낸
    # 나머지에서만 긍정·부정을 읽는다.
    found = _built("네트워크 안정된 장비는?")

    assert found["polarity"] == "positive"
    assert [item["label"] for item in found["matches"]] == ["CVD #3", "CVD #5"]


def test_cites_both_the_name_and_the_mark_of_every_listed_row() -> None:
    found = _built("네트워크가 불안정한 장비는?")

    for item in found["matches"]:
        assert item["label_reference"].startswith(f"{SHEET}!D")
        assert item["value_reference"].startswith(f"{SHEET}!F")


def test_ignores_a_question_without_a_clear_condition() -> None:
    assert _built("장비가 총 몇 대야?") is None
    assert _built("네트워크 안정 상태를 알려줘") is None


def _counted(question: str):
    from app.agent.tools.workbook_row_counts import build_row_count

    rows = _rows()
    return build_row_count(rows, build_header_context(tuple(rows), rows), question)


def test_counts_the_named_column() -> None:
    found = _counted("장비가 총 몇 대야?")

    assert found["header"] == "장비"
    assert found["count"] == len(MARKS)
    assert found["header_reference"] == f"{SHEET}!D5"


def test_does_not_count_a_column_the_question_never_names() -> None:
    # '몇'만 보고 아무 열이나 세면 엉뚱한 수가 근거 확인 딱지를 달고 나간다.
    assert _counted("몇 개야?") is None
    assert _counted("IP가 몇 개야?") is None


def test_ignores_a_question_that_is_not_about_counting() -> None:
    assert _counted("네트워크가 불안정한 장비는?") is None
