"""Complete indexed tables and streaming sources expose the same ranking rows."""
from dataclasses import replace

import pytest

from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter
from tests.support.large_workbook_fixtures import equal, offline, parsed, plan_for, tiny_caps, workbook


@pytest.mark.parametrize("streamed,provider", [(False, False), (False, True), (True, True)])
def test_top_one_hundred_has_identical_output_for_full_index_and_source_scan(request, streamed, provider):
    if streamed:
        request.getfixturevalue("tiny_caps")
    rows = [["Record", "Amount"], *[[f"Item{n}", n] for n in range(1, 121)]]
    summary, index, _ = parsed(workbook({"Records": rows}))
    if not provider:
        index = replace(index, source_provider=None)
    plan = plan_for(summary, operation="row_list", columns=("A", "B"), order_by="B", limit=100)
    answer = execute_tabular_query(plan, summary, index, "Amount 상위 100개 Record와 Amount 보여줘")
    assert answer is not None and answer.verification.level == "request_checked"
    output = [line for line in answer.answer.splitlines() if line.startswith("Record:")]
    assert len(output) == 100
    assert output[0] == "Record: Item120; Amount: 120"
    assert output[-1] == "Record: Item21; Amount: 21"
    assert not answer.limitations
    assert ("full_source_scan" in answer.verification.checks) is streamed
    assert ("stream_original_table" in answer.selected_tools) is streamed


@pytest.mark.parametrize("streamed", [False, True])
def test_boundary_tie_policy_is_identical_with_full_index_or_rescan(request, streamed):
    if streamed:
        request.getfixturevalue("tiny_caps")
    rows = [["Record", "Amount"], ["First", 20], ["Second", 20], ["Third", 20], ["Fourth", 20]]
    summary, index, _ = parsed(workbook({"Records": rows}))
    plan = plan_for(summary, operation="row_list", columns=("A", "B"), order_by="B", limit=2)
    answer = execute_tabular_query(plan, summary, index, "Amount 상위 2개 Record와 Amount 보여줘")
    assert answer is not None
    assert "Record: First; Amount: 20" in answer.answer and "Record: Second; Amount: 20" in answer.answer
    assert "Third" not in answer.answer
    assert "경계값이 같은 행은 원본 행 순서로 선택하여 2개 행만 표시" in answer.answer
    assert ("full_source_scan" in answer.verification.checks) is streamed


def test_stored_source_rank_filter_without_order_by_keeps_existing_path():
    rows = [["Record", "Amount", "Position"], ["Low", 5, 3], ["High", 20, 1], ["Middle", 10, 2]]
    summary, index, _ = parsed(workbook({"Records": rows}))
    plan = plan_for(summary, operation="row_list", columns=("A", "B"), filters=[
        TabularFilter(column_id="C", operator="less_than_or_equal", value=2),
    ])
    answer = execute_tabular_query(plan, summary, index, "Amount 상위 2개 Record와 Amount 보여줘")
    assert answer is not None
    assert "Record: High; Amount: 20" in answer.answer and "Record: Middle; Amount: 10" in answer.answer
    assert "Low" not in answer.answer and answer.selected_tools == ["tabular_query"]
    assert index.source_provider._budget.reads == 0


@pytest.mark.parametrize("streamed", [False, True])
@pytest.mark.parametrize("grouped", [False, True])
@pytest.mark.parametrize("excluded", ["=MISSING_EXTERNAL_VALUE()", "unknown", 0.5])
def test_excluded_measure_does_not_block_small_or_large_tables(request, streamed, grouped, excluded):
    if streamed:
        request.getfixturevalue("tiny_caps")
    rows = [["Record", "Amount", "Department", "State"], ["First", 10, "Alpha", "active"],
            ["Second", 30, "Alpha", "active"], ["Third", 20, "Beta", "active"],
            ["Excluded", excluded, "Gamma", "inactive"]]
    book = workbook({"Records": rows})
    if excluded == 0.5:
        book.active["B5"].number_format = "0%"
    summary, index, _ = parsed(book)
    assert index.truncated_for({"Records"}) is streamed
    plan = plan_for(summary, operation="numeric_summary" if grouped else "row_list",
                    columns=("B",) if grouped else ("A", "B"), group_by=["C"] if grouped else [],
                    order_by="B", limit=2, filters=[equal("D", "active")])
    question = ("State가 active인 Department별 Amount 합계 상위 2개 보여줘" if grouped else
                "State가 active인 Amount 상위 2개 Record와 Amount 보여줘")
    answer = execute_tabular_query(plan, summary, index, question)
    assert answer is not None and answer.verification.level == "request_checked"
    assert "Gamma" not in answer.answer and "Excluded" not in answer.answer
    assert "합계 40" in answer.answer if grouped else "Record: Second; Amount: 30" in answer.answer
    assert ("full_source_scan" in answer.verification.checks) is (streamed or str(excluded).startswith("="))
