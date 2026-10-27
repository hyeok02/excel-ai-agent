"""Independent populations prove connective/parenthesis preservation."""
import pytest

from app.agent.query.boolean_filter_language import parse_boolean
from app.agent.query.boolean_source_answers import boolean_source_answer
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture

MATRIX = [["Item", "Region", "Status", "Amount"], ["A", "North", "Open", 10],
          ["B", "South", "Closed", 20], ["C", "West", "Open", 30], ["D", "South", "Open", 40]]


def fixture(matrix=None):
    return table_fixture([(1, 1, matrix or MATRIX)])


def query_plan(question, summary, **changes):
    table = build_query_tables(summary)[0]
    parsed = parse_boolean(question, table)
    assert parsed is not None
    return TabularQueryPlan(operation="numeric_summary", table_id=table.id,
        column_ids=["D"], statistic="sum", filters=parsed.filters,
        filter_expression=parsed.expression, **changes)


@pytest.mark.parametrize("condition, expected", [
    ("(Region = 'North' OR Region = 'South') AND NOT Status = 'Closed'", 50),
    ("Region = 'North' OR Region = 'South' AND Status = 'Closed'", 30),
    ("(Region = 'North' OR Region = 'South') AND Status = 'Closed'", 20),
    ("NOT (Region = 'West' OR Status = 'Closed')", 50),
    ("(Region이 West 또는 Status가 Closed) 제외", 50),
    ("Region이 North이거나 Region이 South이고 Status가 Closed가 아닌", 50),
    ("(Region이 North 또는 South) 그리고 Status가 Closed가 아닌", 50),
    ("Amount >= 20 AND (Region = 'North' OR Region = 'South')", 60),
])
@pytest.mark.parametrize("reverse", [False, True])
def test_source_boolean_answers_preserve_precedence_and_row_order(condition, expected, reverse):
    matrix = [MATRIX[0], *reversed(MATRIX[1:])] if reverse else MATRIX
    summary, index = fixture(matrix)
    result = boolean_source_answer(condition + " Amount 합계", summary, index)
    assert result.status == "answered" and result.verification.level == "request_checked", result
    assert f"합계 {expected} " in result.answer
    assert "OR" in result.answer


def test_flattened_or_plan_cannot_get_checked_badge():
    summary, index = fixture()
    question = "(Region = 'North' OR Region = 'South') Amount 합계"
    plan = query_plan(question, summary)
    assert execute_tabular_query(plan.model_copy(update={"filter_expression": None}), summary, index, question) is None
    wrong = plan.filter_expression.model_copy(update={"operator": "and"})
    assert execute_tabular_query(plan.model_copy(update={"filter_expression": wrong}), summary, index, question) is None


def test_wrong_precedence_and_dropped_condition_are_not_verified():
    summary, index = fixture()
    question = "(Region = 'North' OR Region = 'South') AND Status = 'Open' Amount 합계"
    wrong = query_plan("Region = 'North' OR Region = 'South' AND Status = 'Open' Amount 합계", summary)
    assert execute_tabular_query(wrong, summary, index, question) is None
    partial = query_plan("Region = 'North' OR Region = 'South' Amount 합계", summary)
    assert execute_tabular_query(partial, summary, index, question) is None


def test_quoted_connectives_parentheses_and_whitespace_are_literal_values():
    matrix = [["Item", "Label", "Amount"], ["A", "A OR B", 10], ["B", "NOT (X)", 20],
              ["C", "alpha  beta", 30], ["D", "alpha beta", 40]]
    summary, index = fixture(matrix)
    result = boolean_source_answer("Label = 'A OR B' OR Label = 'NOT (X)' Amount 합계", summary, index)
    assert result.status == "answered" and "합계 30 " in result.answer
    assert 'Label = "A OR B"' in result.answer and 'Label = "NOT (X)"' in result.answer
    result = boolean_source_answer("Label = 'alpha  beta' OR Label = 'missing' Amount 합계", summary, index)
    assert result.status == "answered" and "합계 30 " in result.answer


def test_unknown_quoted_value_is_a_verified_zero_not_a_guessed_alias():
    summary, index = fixture()
    result = boolean_source_answer("Region = 'Unknown1' OR Region = 'Unknown2' 행 수", summary, index)
    assert result.status == "answered" and "0건" in result.answer


@pytest.mark.parametrize("extra", ["2024년", "최근 1년", "승인된", "중 서울", "그리고 미완료", "AND Missing = 'A'"])
def test_unknown_extra_condition_never_disappears(extra):
    summary, index = fixture()
    result = boolean_source_answer(f"Region = 'North' OR Region = 'South' {extra} Amount 합계", summary, index)
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"


def test_normal_legacy_and_still_works_without_expression():
    summary, index = fixture()
    question = "Region = 'South' AND Status = 'Open' Amount 합계"
    plan = query_plan(question, summary).model_copy(update={"filter_expression": None})
    answer = execute_tabular_query(plan, summary, index, question)
    assert answer.status == "answered" and "합계 40 " in answer.answer


def test_different_operator_than_question_is_rejected():
    summary, index = fixture()
    question = "Amount >= 20 OR Region = 'North' Amount 합계"
    plan = query_plan(question, summary)
    bad = plan.filters[0].model_copy(update={"operator": "less_than"})
    assert execute_tabular_query(plan.model_copy(update={"filters": [bad, plan.filters[1]]}), summary, index, question) is None
