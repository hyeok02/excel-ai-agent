"""Partial source-text predicates preserve the named column and earlier filters."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture
from tests.test_tabular_request_adversarial import _answer


@pytest.mark.parametrize("column,valid", [("D", True), ("C", False), ("B", False)])
def test_contains_filter_stays_bound_to_the_requested_source_field(column, valid):
    summary, index = table_fixture([(2, 1, [
        ["Asset", "Connection", "Review", "Change"],
        ["Unit #31", "x", "o", "New (scheduled)"],
        ["Unit #32", "o", "x", "New (reviewed)"],
        ["Unit #33", "x", "x", "Existing"],
    ])])
    plan = TabularQueryPlan(operation="row_list", table_id=build_query_tables(summary)[0].id,
                            column_ids=["A", "B", "D"], filters=[
                                TabularFilter(column_id="B", operator="equals", value="x"),
                                TabularFilter(column_id=column, operator="contains", value="New")])
    question = "Connection이 x이고 Change contains New인 Asset만 보여줘"
    answer = _answer(question, plan, summary, index, "row_list")
    assert (answer is not None) == valid
    if valid:
        assert "Unit #31" in answer.answer
        assert "Unit #32" not in answer.answer and "Unit #33" not in answer.answer


def test_unknown_literal_value_still_uses_the_explicit_field_without_inventing_rows():
    summary, index = table_fixture([(2, 1, [
        ["Asset", "Connection", "Review"], ["First", "x", "o"], ["Second", "o", "x"],
    ])])
    plan = TabularQueryPlan(operation="row_list", table_id=build_query_tables(summary)[0].id,
                            column_ids=["A"], filters=[
                                TabularFilter(column_id="B", operator="equals", value="pending")])
    answer = _answer("Connection이 pending인 Asset", plan, summary, index, "row_list")
    assert answer is not None and "맞는 행이 없습니다" in answer.answer
    plan.filters[0].column_id = "C"
    assert _answer("Connection이 pending인 Asset", plan, summary, index, "row_list") is None
