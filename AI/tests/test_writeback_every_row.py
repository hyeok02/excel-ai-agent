"""An "every X" edit reaches every matching row or none; a Korean column word names one header."""
from io import BytesIO

from openpyxl import Workbook

from tests.support.writeback_target_fixtures import proposal


def _content(carrots=3):
    book = Workbook()
    sheet = book.active
    sheet.title = "Sales"
    sheet.append(["ID", "Product", "Qty", "UnitPrice"])
    prices = [1.7699999999999998, 2.0, 3.5]
    for number in range(carrots):
        sheet.append([f"A{number}", "Carrot", 10 + number, prices[number % 3]])
        if number == 0:
            sheet.append(["B0", "Banana", 5, 2.27])
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def _changes(body):
    return {change["reference"]: change["new_value"] for change in body["changes"]}


def test_a_partial_every_row_draft_is_completed_with_computed_values() -> None:
    body = proposal("모든 Carrot의 UnitPrice를 10% 올려줘", [("Sales", "D2", 1.947)], _content())
    assert body["status"] == "ready", body
    assert _changes(body) == {"D2": 1.947, "D4": 2.2, "D5": 3.85}
    assert any("3개 행 전체" in item for item in body["limitations"])


def test_a_stated_value_after_the_object_marker_reaches_every_row() -> None:
    body = proposal("Carrot UnitPrice를 전부 2.5로 바꿔줘", [("Sales", "D4", 2.5)], _content())
    assert _changes(body) == {"D2": 2.5, "D4": 2.5, "D5": 2.5}
    assert proposal("Carrot UnitPrice를 2.5로 바꿔줘", [("Sales", "D4", 2.5)], _content())["status"] == "blocked"


def test_every_matching_row_is_proposed_however_many_there_are() -> None:
    body = proposal("모든 Carrot의 UnitPrice를 10% 올려줘", [("Sales", "D2", 1.947)], _content(carrots=210))
    assert body["status"] == "ready" and len(body["changes"]) == 210


def test_a_korean_column_word_is_read_as_the_one_drafted_header_and_said_so() -> None:
    body = proposal("모든 Carrot의 단가를 10% 내려줘", [("Sales", "D2", 1.593)], _content())
    assert body["status"] == "ready", body
    assert _changes(body) == {"D2": 1.593, "D4": 1.8, "D5": 3.15}
    assert any("‘단가’를 원본 ‘UnitPrice’ 열로 해석" in item for item in body["limitations"])


def test_unknown_words_in_the_header_script_or_two_unknown_words_stay_blocked() -> None:
    for instruction in ("모든 Carrot의 UnitCost를 10% 내려줘", "모든 당근의 단가를 10% 내려줘"):
        assert proposal(instruction, [("Sales", "D2", 1.593)], _content())["status"] == "blocked"
