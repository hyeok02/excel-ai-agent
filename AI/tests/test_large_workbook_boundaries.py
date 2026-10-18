"""Real original index limits, not only reduced caps, must preserve tail data."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query import index as index_module
from tests.support.large_workbook_fixtures import (
    ask, assert_stream_checked, equal, fresh_index, offline, parsed, plan_for, tiny_caps, workbook,
)


@pytest.fixture(scope="module")
def row_limit_source():
    matrix = [["Record", "Amount"]]
    matrix.extend([f"Item{number}", 1] for number in range(1, 10_002))
    matrix.append(["Tail", 9_999])
    return parsed(workbook({"Records": matrix}))


@pytest.mark.parametrize("statistic,expected", [
    ("sum", "합계 20,000"), ("max", "최댓값 9,999"), ("min", "최솟값 1"),
])
def test_actual_ten_thousand_row_limit_rescans_tail(row_limit_source, statistic, expected):
    summary, _, content = row_limit_source
    index = fresh_index(summary, content)
    assert index.truncated_for({"Records"})
    assert not build_query_tables(summary)[0].complete
    plan = plan_for(summary, statistic=statistic)
    operation = {"sum": "합계", "max": "최대", "min": "최소"}[statistic]
    answer = ask(f"Records 시트 Amount {operation}는?", summary, index, plan)
    assert_stream_checked(answer)
    assert expected in answer.answer
    assert "숫자 10002건" in answer.answer
    assert any("10003" in item.reference for item in answer.evidence)


def test_actual_fifty_thousand_cell_limit_rescans_tail_values():
    matrix = [["Record", "Amount", "Group", "Spare", "Other", "Marker"]]
    matrix.extend([f"Item{number}", 1, "regular", "text", 2, "present"] for number in range(1, 8_334))
    matrix.append(["Tail", 17, "last", "text", 2, "present"])
    summary, index, _ = parsed(workbook({"Records": matrix}))
    assert index.indexed_cell_count == 50_000 and index.truncated_for({"Records"})
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_stream_checked(answer)
    assert "합계 8,350" in answer.answer and "숫자 8334건" in answer.answer


@pytest.mark.parametrize("operation,statistic,expected", [
    ("row_count", "sum", "8건"), ("numeric_summary", "sum", "합계 36"),
    ("numeric_summary", "average", "평균 4.5"),
])
def test_summary_sample_and_index_caps_are_independent(tiny_caps, operation, statistic, expected):
    matrix = [["Record", "Amount"], *[[f"Item{number}", number] for number in range(1, 9)]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    columns = () if operation == "row_count" else ("B",)
    plan = plan_for(summary, operation=operation, columns=columns, statistic=statistic)
    question = "Records 시트 전체 행 개수는?" if not columns else f"Records 시트 Amount {statistic}은?"
    answer = ask(question, summary, index, plan)
    assert_stream_checked(answer)
    assert expected in answer.answer


def test_exact_lookup_can_find_the_only_match_beyond_index_and_sample(tiny_caps):
    matrix = [["Record", "Amount"], *[[f"Item{n}", n] for n in range(8)], ["Tail", 4321]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    plan = plan_for(summary, operation="lookup", filters=[equal("A", "Tail")])
    answer = ask("Records 시트 Record가 Tail인 Amount 값은?", summary, index, plan)
    assert_stream_checked(answer)
    assert "4321" in answer.answer or "4,321" in answer.answer


def test_complete_index_does_not_hide_an_incomplete_summary_sample(tiny_caps, monkeypatch):
    monkeypatch.setattr(index_module, "MAX_INDEXED_CELLS", 1000)
    monkeypatch.setattr(index_module, "MAX_ROWS_PER_SHEET", 100)
    matrix = [["Record", "Amount"], *[[f"Item{n}", n] for n in range(1, 9)]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    assert not index.truncated
    assert not build_query_tables(summary)[0].complete
    answer = ask("Records 시트 Amount 합계는?", summary, index, plan_for(summary))
    assert_stream_checked(answer)
    assert "합계 36" in answer.answer
