"""Source rescans retain explicit scope guards and existing small-table paths."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables, query_catalog
from app.agent.query.tabular_execution import execute_tabular_query
from tests.support.large_workbook_fixtures import (
    offline, parsed, plan_for, tiny_caps, workbook,
)


def source_rows():
    return [["Record", "Amount", "Group"], *[[f"Item{n}", n, "ordinary"] for n in range(1, 9)]]


def test_sheet_name_substring_does_not_become_a_requested_source_header(tiny_caps):
    summary, index, _ = parsed(workbook({"Records": source_rows()}))
    answer = execute_tabular_query(plan_for(summary), summary, index, "Records 시트 Amount 합계는?")
    assert answer is not None and "합계 36" in answer.answer
    assert "full_source_scan" in answer.verification.checks


@pytest.mark.parametrize("sheet", ["Records", "Amount"])
def test_explicit_actual_header_is_still_required_after_removing_sheet_scope(tiny_caps, sheet):
    summary, index, _ = parsed(workbook({sheet: source_rows()}))
    plan = plan_for(summary, sheet=sheet, operation="row_list")
    assert execute_tabular_query(plan, summary, index, f"{sheet} 시트 Record와 Amount 보여줘") is None


def test_explicit_subrange_cannot_certify_the_whole_table_row_count(tiny_caps):
    summary, index, _ = parsed(workbook({"Records": source_rows()}))
    plan = plan_for(summary, operation="row_count", columns=())
    assert execute_tabular_query(plan, summary, index, "'Records'!A5:C8 범위 행 개수는?") is None


def test_incomplete_catalog_separates_sample_size_from_population(tiny_caps):
    summary, _, _ = parsed(workbook({"Records": source_rows()}))
    table = build_query_tables(summary)[0]
    entry = query_catalog(summary, "Amount 합계")[0]
    assert not table.complete and len(table.rows) < 8
    assert entry["range"] == "A1:C9" and entry["row_count"] is None
    assert entry["sampled_row_count"] == len(table.rows)


@pytest.mark.parametrize("all_attributes", [False, True])
def test_fully_indexed_small_table_keeps_sorted_path_on_a_truncated_sheet(tiny_caps, all_attributes):
    book = workbook({"Records": [["Record", "Amount"], ["First", 10], ["Second", 20]]})
    book.active["A10"] = "Unrelated tail outside the native table"
    summary, index, _ = parsed(book)
    table = build_query_tables(summary)[0]
    assert table.complete and index.truncated_for({"Records"})
    assert query_catalog(summary, "Amount")[0]["row_count"] == 2
    plan = plan_for(summary, operation="row_list", columns=("A", "B"), order_by="B", limit=1,
                    column_scope="all_attributes" if all_attributes else "selected")
    answer = execute_tabular_query(
        plan, summary, index, "Records 시트 Amount 기준 상위 1개 Record와 Amount 보여줘")
    assert answer is not None and "Second" in answer.answer and "20" in answer.answer
    assert answer.verification.level == "request_checked"
    assert answer.selected_tools == ["tabular_query"]
    assert index.source_provider._budget.reads == 0
