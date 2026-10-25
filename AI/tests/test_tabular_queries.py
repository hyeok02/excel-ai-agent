from dataclasses import replace

import pytest

from app.agent.query.tabular_catalog import build_query_tables, query_catalog
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("headers,rows,column", [
    (["Asset", "Readiness"], [["Q1", "ready"], ["Q2", "repair"], ["Q3", None]], "D"),
    (["검토 단계", "요청 코드"], [["대기", "Z1"], ["승인", "Z2"], [None, "Z3"]], "C"),
    (["Decorative label", "Item"], [["○ note", "A"], ["○", "B"], [None, "C"]], "C"),
])
def test_arbitrary_renamed_reordered_categories_preserve_exact_values(headers, rows, column):
    summary, index = table_fixture([(5, 3, [headers] + rows)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="frequencies", table_id=table.id, column_ids=[column])
    answer = execute_tabular_query(plan, summary, index, "표시별 건수")
    assert answer is not None and answer.status == "answered"
    position = ord(column) - ord("C")
    for row in rows:
        if row[position] is not None:
            assert f"‘{row[position]}’ 1건" in answer.answer
    assert "빈칸 1건" in answer.answer and "총 3건" in answer.answer
    assert len(answer.evidence) == 2
    assert query_catalog(summary, headers[position])[0]["table_id"] == table.id


def test_multiple_tables_keep_separate_counts_and_exact_evidence_ranges():
    summary, index = table_fixture([
        (2, 2, [["Object", "Flag"], ["A", "pending"], ["B", "pending"]]),
        (9, 5, [["Object", "Flag"], ["A", "ready"], ["B", None], ["C", "ready"]]),
    ])
    tables = build_query_tables(summary)
    assert [table.id for table in tables] == ["Arbitrary!B2:C4", "Arbitrary!E9:F12"]
    plan = TabularQueryPlan(operation="frequencies", table_id=tables[1].id, column_ids=["F"])
    # Same-shaped tables with different values: only a named scope selects one.
    assert execute_tabular_query(plan, summary, index, "second table flags") is None
    answer = execute_tabular_query(plan, summary, index, "Arbitrary!E9:F12 flags")
    assert "‘ready’ 2건" in answer.answer and "빈칸 1건" in answer.answer
    assert "pending" not in answer.answer
    assert {item.reference for item in answer.evidence} == {"E9:E12", "F9:F12"}


def test_numeric_summary_and_filtered_row_count_are_source_computed():
    summary, index = table_fixture([(1, 1, [
        ["Item", "Amount", "Class"], ["A", 10, "red"],
        ["B", 20, "blue"], ["C", None, "red"], ["D", -6, "red"],
    ])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"],
                            filters=[TabularFilter(column_id="C", operator="equals", value="red")])
    answer = execute_tabular_query(plan, summary, index, "red amounts")
    assert "합계 4" in answer.answer and "평균 2" in answer.answer
    assert "최솟값 -6" in answer.answer and "최댓값 10" in answer.answer
    assert "빈칸 1건" in answer.answer
    count_plan = plan.model_copy(update={"operation": "row_count"})
    assert execute_tabular_query(count_plan, summary, index, "count") is None
    count = execute_tabular_query(count_plan, summary, index, "red count")
    assert "3건" in count.answer


@pytest.mark.parametrize("mutation", ["incomplete", "bad_column", "stale", "missing_row", "formula"])
def test_incomplete_invalid_or_stale_sources_cannot_return_verified_answers(mutation):
    summary, index = table_fixture([(1, 1, [["Item", "State"], ["A", "one"], ["B", None]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="frequencies", table_id=table.id, column_ids=["B"])
    if mutation == "incomplete":
        summary.sheets[0].regions[0].analysis_rows[0][0]["value"] = "changed"
        summary.sheets[0].regions[0] = replace(summary.sheets[0].regions[0], analysis_complete=False)
    elif mutation == "bad_column":
        plan = plan.model_copy(update={"column_ids": ["Z"]})
    elif mutation == "stale":
        summary.sheets[0].regions[0].analysis_rows[1][1]["value"] = "different"
    elif mutation == "missing_row":
        index = replace(index, rows=index.rows[:-1])
    else:
        summary.sheets[0].regions[0].analysis_rows[-1].append(
            {"address": "B3", "value": None, "formula": "=1+1", "cached_value": None}
        )
    assert execute_tabular_query(plan, summary, index, "states") is None


def test_partial_index_returns_limited_only_if_target_range_was_fully_scanned():
    summary, index = table_fixture([(1, 1, [["Item", "State"], ["A", "yes"], ["B", "no"]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="frequencies", table_id=table.id, column_ids=["B"])
    index = replace(index, truncated=True, truncated_sheet_names=frozenset({"Arbitrary"}))
    answer = execute_tabular_query(plan, summary, index, "states")
    assert answer.status == "limited"
    assert execute_tabular_query(plan, summary, replace(index, rows=index.rows[:-1]), "states") is None
