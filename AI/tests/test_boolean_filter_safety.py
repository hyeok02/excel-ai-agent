"""No missing numeric value, malformed tree, wrong unit or unsupported join is certified."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from app.agent.query.boolean_filter_models import BooleanFilterExpression as Node
from app.agent.query.boolean_filter_language import boolean_question
from app.agent.query.boolean_source_answers import boolean_source_answer
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.support.large_workbook_fixtures import offline, parsed, workbook
from tests.test_boolean_filter_queries import fixture, query_plan


def test_plan_tree_requires_every_filter_once():
    leaf = {"operator": "predicate", "filter_index": 0}
    condition = {"column_id": "B", "operator": "equals", "value": "A"}
    for expression in [leaf, {"operator": "or", "children": [leaf, leaf]},
                       {"operator": "not", "children": [leaf, leaf]}]:
        with pytest.raises(ValidationError):
            TabularQueryPlan(operation="row_count", table_id="test", filters=[condition, condition],
                             filter_expression=expression)


def test_tree_depth_is_bounded_even_if_each_node_has_valid_shape():
    node = Node(operator="predicate", filter_index=0)
    for _ in range(6):
        node = Node(operator="not", children=[node])
    with pytest.raises(ValidationError):
        TabularQueryPlan(operation="row_count", table_id="test",
            filters=[{"column_id": "B", "operator": "equals", "value": "A"}], filter_expression=node)


def test_runtime_rechecks_forged_or_incomplete_expression():
    summary, index = fixture()
    question = "Region = 'North' OR Region = 'South' Amount 합계"
    plan = query_plan(question, summary)
    forged = plan.model_copy(update={"filter_expression": Node(operator="predicate", filter_index=0)})
    assert execute_tabular_query(forged, summary, index, question) is None


def test_numeric_missing_is_not_converted_to_zero_under_not():
    summary, index = fixture([["Item", "Amount"], ["A", 10], ["B", None], ["C", 30]])
    result = boolean_source_answer("NOT (Amount > 20) 행 수", summary, index)
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"
    result = boolean_source_answer("Amount is blank OR Amount > 20 행 수", summary, index)
    assert result.status == "answered" and "2건" in result.answer


def test_legacy_not_equals_plan_cannot_bypass_unknown_semantics_for_explicit_not():
    summary, index = fixture([["Item", "Region", "Status", "Amount"],
                              ["A", "North", "Open", 10], ["B", "South", "#N/A", 90]])
    question = "NOT Status = 'Closed' Amount 합계"
    plan = query_plan(question, summary)
    legacy = plan.model_copy(update={"filter_expression": None,
        "filters": [plan.filters[0].model_copy(update={"operator": "not_equals"})]})
    assert execute_tabular_query(legacy, summary, index, question) is None


def test_explicit_nonblank_condition_resolves_numeric_missing_scope():
    summary, index = fixture([["Item", "Amount"], ["A", 10], ["B", None], ["C", 30]])
    result = boolean_source_answer("Amount is not blank AND NOT (Amount > 20) 행 수", summary, index)
    assert result.status == "answered" and "1건" in result.answer


def test_decisive_true_or_unknown_still_has_a_proven_population():
    summary, index = fixture([["Item", "Amount"], ["A", None], ["B", 30]])
    result = boolean_source_answer("Item = 'A' OR Amount > 20 행 수", summary, index)
    assert result.status == "answered" and "2건" in result.answer


def test_percent_comparison_uses_source_display_scale():
    book = workbook({"Records": [["Item", "Rate"], ["A", 0.1], ["B", 0.2], ["C", 0.05]]})
    for row in book.active.iter_rows(min_row=2, min_col=2):
        row[0].number_format = "0%"
    summary, index, _ = parsed(book)
    result = boolean_source_answer("Rate >= 15% OR Item = 'A' 행 수", summary, index)
    assert result.status == "answered" and "2건" in result.answer
    summary, index = fixture([["Item", "Rate"], ["A", 0.1], ["B", 0.2]])
    result = boolean_source_answer("Rate >= 15% OR Item = 'A' 행 수", summary, index)
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"


def test_calendar_dates_are_not_compared_as_strings_or_excel_numbers():
    book = workbook({"Records": [["Item", "Date"], ["A", datetime(2024, 1, 1)], ["B", datetime(2025, 1, 1)]]})
    summary, index, _ = parsed(book)
    result = boolean_source_answer("Date = '2024-01-01' OR Item = 'Z' 행 수", summary, index)
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"


def test_quoted_not_is_not_a_boolean_operator_and_legacy_is_not_stays_legacy():
    assert not boolean_question("Label = 'NOT (X)' 행 수")
    assert not boolean_question("Status is not 'Closed' 행 수")
    assert not boolean_question("Revenue (Online AND Retail) 합계")
    assert boolean_question("NOT Status = 'Closed' 행 수")


def test_relational_plan_rejects_boolean_field_rather_than_flattening_it():
    from app.agent.query.relational_models import RelationalQueryPlan
    with pytest.raises(ValidationError):
        RelationalQueryPlan(operation="row_count", left_table_id="left", right_table_id="right",
            on=[{"left_column_id": "A", "right_column_id": "A"}],
            filter_expression={"operator": "predicate", "filter_index": 0})
