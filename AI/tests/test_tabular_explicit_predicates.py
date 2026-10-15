"""Absent or partial source values still impose mandatory request predicates."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture
from tests.test_tabular_request_adversarial import _answer


def _run(question, filters, matrix=None):
    matrix = matrix or [
        ["Asset", "Connection", "Review", "Change"],
        ["First", "x", "o", "New (scheduled)"],
        ["Second", "o", "x", "New (reviewed)"],
        ["Third", "x", "x", "Existing"],
    ]
    summary, index = table_fixture([(2, 1, matrix)])
    plan = TabularQueryPlan(operation="row_list", table_id=build_query_tables(summary)[0].id,
                            column_ids=[column.id for column in build_query_tables(summary)[0].columns],
                            filters=[TabularFilter(column_id=column, operator=operator, value=value)
                                     for column, operator, value in filters])
    return _answer(question, plan, summary, index, "row_list")


@pytest.mark.parametrize("operator", [None, "equals", "not_equals", "contains"])
def test_partial_contains_value_cannot_change_operator_or_disappear(operator):
    filters = [("B", "equals", "x")]
    if operator:
        filters.append(("D", operator, "New"))
    answer = _run("Connection이 x이고 Change contains New인 Asset만 보여줘", filters)
    assert (answer is not None) == (operator == "contains")
    if answer:
        assert "Asset: First" in answer.answer and "Asset: Third" not in answer.answer


@pytest.mark.parametrize("operator", [None, "equals", "not_equals"])
@pytest.mark.parametrize("negative", [False, True])
def test_absent_value_preserves_equality_or_exclusion_and_cannot_be_omitted(operator, negative):
    question = "Connection is not pending인 Asset" if negative else "Connection이 pending인 Asset"
    filters = [("B", operator, "pending")] if operator else []
    answer = _run(question, filters)
    assert (answer is not None) == (operator == ("not_equals" if negative else "equals"))


@pytest.mark.parametrize("second", [False, True])
def test_each_named_field_keeps_the_same_unknown_value_predicate(second):
    filters = [("B", "equals", "pending")]
    if second:
        filters.append(("C", "equals", "pending"))
    assert (_run("Connection이 pending이고 Review가 pending인 Asset", filters) is not None) == second


@pytest.mark.parametrize("column", ["C", "D"])
def test_korean_contains_prefix_stays_bound_to_its_source_field(column):
    assert (_run("Change에 포함된 New인 Asset만 보여줘", [(column, "contains", "New")])
            is not None) == (column == "D")


@pytest.mark.parametrize("operator", ["equals", "contains"])
def test_next_clause_operator_cannot_leak_into_the_previous_predicate(operator):
    answer = _run("State=x, Tag 포함 New인 Asset", [("B", operator, "x"), ("C", "contains", "New")], [
        ["Asset", "State", "Tag"], ["First", "x", "New"],
        ["Second", "x1", "New"], ["Third", "o", "Old"],
    ])
    assert (answer is not None) == (operator == "equals")
    if answer:
        assert "Asset: First" in answer.answer and "Asset: Second" not in answer.answer


def test_an_extra_operator_on_the_same_partial_value_is_not_authorized():
    answer = _run("Change contains New인 Asset", [
        ("D", "contains", "New"), ("D", "not_equals", "New"),
    ])
    assert answer is None


@pytest.mark.parametrize("column", [None, "B", "C"])
@pytest.mark.parametrize("negative", [False, True])
def test_blank_condition_cannot_move_to_another_field_or_disappear(column, negative):
    suffix = "빈칸이 아닌" if negative else "빈칸인"
    operator = "not_blank" if negative else "is_blank"
    filters = [(column, operator, None)] if column else []
    answer = _run(f"Connection이 {suffix} Asset만 보여줘", filters, [
        ["Asset", "Connection", "Review"], ["First", None, "x"],
        ["Second", "x", None], ["Third", "o", "o"],
    ])
    assert (answer is not None) == (column == "B")


@pytest.mark.parametrize("value,valid", [(None, False), ("None", True)])
def test_literal_none_is_not_a_blank_value(value, valid):
    answer = _run("Connection이 'None'인 Asset", [("B", "equals", value)], [
        ["Asset", "Connection"], ["First", None], ["Second", "None"],
    ])
    assert (answer is not None) == valid
    if answer:
        assert "Asset: Second" in answer.answer and "Asset: First" not in answer.answer


@pytest.mark.parametrize("value,valid", [("x", True), ("x and", False)])
def test_english_conjunction_is_not_part_of_a_predicate_value(value, valid):
    answer = _run("Connection=x and Review contains New인 Asset", [
        ("B", "equals", value), ("C", "contains", "New"),
    ], [["Asset", "Connection", "Review"], ["First", "x", "New"]])
    assert (answer is not None) == valid
