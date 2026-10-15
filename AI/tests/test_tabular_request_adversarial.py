"""A source-valid computation must also preserve every explicit request constraint."""
from dataclasses import replace

import pytest

from app.agent.query import tabular_execution
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


def _fixture():
    return table_fixture([(7, 3, [
        ["Record ID", "Status", "Amount"],
        ["JOB-27", "Done", 100], ["JOB-28", "Pending", 200],
        ["JOB-29", "Done", 300],
    ])], sheet_name="Renamed Records")


def _answer(question, plan, summary, index, kind):
    return execute_tabular_query(plan, summary, index, question,
                                 QuestionIntent(False, kind, (), True, plan))


@pytest.mark.parametrize("filters", [
    [],
    [TabularFilter(column_id="D", operator="equals", value="Pending")],
    [TabularFilter(column_id="D", operator="not_equals", value="Done")],
])
def test_request_category_filter_cannot_be_omitted_changed_or_negated(filters):
    summary, index = _fixture()
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id,
                            column_ids=["D"], filters=filters)

    assert _answer("Status가 Done인 건수", plan, summary, index, "row_count") is None


@pytest.mark.parametrize("operator,threshold", [
    ("greater_than", 200),
    ("greater_than_or_equal", 100),
    ("less_than", 100),
])
def test_request_numeric_threshold_and_comparison_boundary_cannot_change(operator, threshold):
    summary, index = _fixture()
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id,
                            filters=[TabularFilter(column_id="E", operator=operator, value=threshold)])

    assert _answer("Amount가 100 초과인 건수", plan, summary, index, "row_count") is None


@pytest.mark.parametrize("updates", [
    {"limit": 1}, {"limit": None}, {"descending": False},
    {"order_by": None}, {"statistic": "average"},
])
def test_request_top_n_order_limit_and_statistic_cannot_change(updates):
    summary, index = _fixture()
    plan = TabularQueryPlan(operation="numeric_summary", table_id=build_query_tables(summary)[0].id,
                            column_ids=["E"], order_by="E", descending=True, limit=2, statistic="sum")
    plan = plan.model_copy(update=updates)

    assert _answer("Amount 상위 2개 합계", plan, summary, index, "aggregation") is None


@pytest.mark.parametrize("asked_id,selected_id", [("JOB-27", "JOB-28"), ("#27", "#28"), ("A12", "A13")])
def test_requested_record_identity_cannot_change_for_non_legacy_id_shapes(asked_id, selected_id):
    summary, index = table_fixture([(12, 6, [
        ["Record ID", "Amount"], [asked_id, 12], [selected_id, 999],
    ])], sheet_name="Alternate")
    plan = TabularQueryPlan(operation="lookup", table_id=build_query_tables(summary)[0].id,
                            column_ids=["G"], filters=[
                                TabularFilter(column_id="F", operator="equals", value=selected_id),
                            ])

    assert _answer(f"{asked_id}의 Amount", plan, summary, index, "cell_lookup") is None


def test_explicit_parallel_table_range_cannot_be_replaced_by_same_headers():
    summary, index = table_fixture([
        (3, 1, [["Record", "Amount"], ["A", 10], ["B", 20]]),
        (3, 6, [["Record", "Amount"], ["X", 100], ["Y", 200]]),
    ])
    tables = build_query_tables(summary)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=tables[0].id,
                            column_ids=["B"], statistic="sum")

    assert _answer("Arbitrary!F3:G5 표의 Amount 합계", plan, summary, index, "aggregation") is None


def test_named_parallel_table_context_cannot_be_ignored(monkeypatch):
    summary, index = table_fixture([
        (3, 1, [["Record", "Amount"], ["A", 10], ["B", 20]]),
        (3, 6, [["Record", "Amount"], ["X", 100], ["Y", 200]]),
    ])
    tables = build_query_tables(summary)
    tables = [replace(tables[0], context=(("Arbitrary!A1", "Active Register"),)),
              replace(tables[1], context=(("Arbitrary!F1", "Archived Register"),))]
    monkeypatch.setattr(tabular_execution, "build_query_tables", lambda _: tables)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=tables[0].id,
                            column_ids=["B"], statistic="sum")

    assert _answer("Archived Register의 Amount 합계", plan, summary, index, "aggregation") is None


def test_correct_explicit_plan_remains_answerable():
    summary, index = _fixture()
    plan = TabularQueryPlan(operation="row_count", table_id=build_query_tables(summary)[0].id,
                            filters=[TabularFilter(column_id="D", operator="equals", value="Done")])
    answer = _answer("Status가 Done인 건수", plan, summary, index, "row_count")

    assert answer is not None and "2건" in answer.answer
    assert answer.verification.level == "request_checked"
