"""Tail headers and subtotals cannot become certified source observations."""
import pytest

from tests.support.large_workbook_fixtures import (
    ask, assert_not_certified, assert_stream_checked, offline, parsed, plan_for,
    tiny_caps, workbook,
)


def plain_source(tail):
    matrix = [["Record", "Amount", "Group"]]
    matrix.extend([f"Item{number}", number, "ordinary"] for number in range(1, 9))
    book = workbook({"Records": matrix + tail})
    book.active.tables.clear()
    return parsed(book)


@pytest.mark.parametrize("header", [
    ["Record", "Amount", "Group"],
    ["Record", "Amount", "Notes"],
])
@pytest.mark.parametrize("operation,columns,question", [
    ("row_count", (), "Records 시트 전체 행 개수는?"),
    ("frequencies", ("C",), "Records 시트 Group 값별 건수는?"),
])
def test_tail_second_header_is_not_a_certified_record(tiny_caps, header, operation, columns, question):
    summary, index, _ = plain_source([header, ["Extra", 900, "other"]])
    plan = plan_for(summary, operation=operation, columns=columns)
    answer = ask(question, summary, index, plan)
    assert_not_certified(answer)
    assert "full_source_scan" not in answer.verification.checks


def test_tail_section_caption_does_not_hide_a_second_header(tiny_caps):
    tail = [["Second section", None, None], ["Record", "Amount", "Notes"], ["Extra", 900, "other"]]
    summary, index, _ = plain_source(tail)
    plan = plan_for(summary, operation="row_count", columns=())
    answer = ask("Records 시트 전체 행 개수는?", summary, index, plan)
    assert_not_certified(answer)


def test_two_column_partial_header_is_not_a_certified_record(tiny_caps):
    matrix = [["Record", "Amount"], *[[f"Item{number}", number] for number in range(1, 9)]]
    book = workbook({"Records": matrix + [["Record", "Other"], ["Extra", 900]]})
    book.active.tables.clear()
    summary, index, _ = parsed(book)
    plan = plan_for(summary, operation="row_count", columns=())
    answer = ask("Records 시트 전체 행 개수는?", summary, index, plan)
    assert_not_certified(answer)


def test_completely_different_tail_header_is_an_ambiguous_plain_table_boundary(tiny_caps):
    summary, index, _ = plain_source([["Product", "Cost", "Category"], ["Extra", 900, "other"]])
    plan = plan_for(summary, operation="row_count", columns=())
    answer = ask("Records 시트 전체 행 개수는?", summary, index, plan)
    assert_not_certified(answer)


def test_tail_section_subtotal_is_not_added_to_its_underlying_records(tiny_caps):
    summary, index, _ = plain_source([["Section subtotal", 36, None]])
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    if answer.status == "answered":
        assert_stream_checked(answer)
        assert "합계 36" in answer.answer and "합계 72" not in answer.answer
    else:
        assert_not_certified(answer)
