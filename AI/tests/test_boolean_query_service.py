"""Public service must route Boolean questions before single-condition shortcuts."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.support.large_workbook_fixtures import NoGeneratedAnswer, FixedClassifier
from tests.test_boolean_filter_queries import fixture, query_plan


def ask(question, summary, index, classifier=None):
    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry(), classifier=classifier)
    return asyncio.run(service.answer(question, summary, index))


def test_ordinary_or_question_needs_no_model_and_does_not_become_first_condition_lookup():
    summary, index = fixture()
    result = ask("Region이 North 또는 South인 행 수", summary, index)
    assert result.status == "answered" and "3건" in result.answer
    assert result.verification.level == "request_checked"


def test_model_plan_can_add_ranking_without_flattening_boolean_population():
    summary, index = fixture()
    question = "(Region = 'North' OR Region = 'South') Amount 상위 2개 Item Amount 목록"
    base = query_plan(question, summary)
    plan = base.model_copy(update={"operation": "row_list", "column_ids": ["A", "D"],
                                   "order_by": "D", "limit": 2})
    result = ask(question, summary, index, FixedClassifier(plan))
    assert result.status == "answered" and result.verification.level == "request_checked", result
    assert "Item: D" in result.answer and "Item: B" in result.answer
    assert "Item: C" not in result.answer


def test_model_flat_and_cannot_rescue_a_boolean_query_with_wrong_population():
    summary, index = fixture()
    question = "(Region = 'North' OR Region = 'South') Amount 상위 2개 Item Amount 목록"
    base = query_plan(question, summary)
    plan = base.model_copy(update={"operation": "row_list", "column_ids": ["A", "D"],
                                  "order_by": "D", "limit": 2, "filter_expression": None})
    result = ask(question, summary, index, FixedClassifier(plan))
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"


@pytest.mark.parametrize("question", ["Region이 South가 아닌 Amount 합계", "Region is not 'South' Amount 합계"])
def test_ordinary_single_exclusion_does_not_require_new_boolean_syntax(question):
    summary, index = fixture()
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["D"], statistic="sum",
                            filters=[{"column_id": "B", "operator": "not_equals", "value": "South"}])
    result = ask(question, summary, index, FixedClassifier(plan))
    assert result.status == "answered" and "합계 40" in result.answer


def test_header_currency_parentheses_are_not_boolean_grouping():
    summary, index = fixture([["Item", "Revenue (USD)"], ["A", 10], ["B", 20]])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"], statistic="sum")
    result = ask("Revenue (USD) 합계", summary, index, FixedClassifier(plan))
    assert result.status == "answered" and "합계 30" in result.answer


def test_currency_parentheses_before_boolean_conditions_stay_source_metadata():
    summary, index = fixture([["Item", "Region", "Revenue (USD)"], ["A", "North", 10], ["B", "South", 20]])
    result = ask("Revenue (USD) 합계: Region = 'North' OR Region = 'South'", summary, index)
    assert result.status == "answered" and "합계 30" in result.answer


def test_boolean_join_request_is_not_replaced_by_one_tables_subpopulation():
    from tests.relational_query_fixtures import relational_fixture, relational_plan
    summary, index = relational_fixture()
    plan = relational_plan(summary, group_by=[], population="matched_only", join_type="inner", filters=[
        {"side": "right", "column_id": "B", "operator": "equals", "value": "North"},
        {"side": "right", "column_id": "B", "operator": "equals", "value": "South"}])

    class Classifier:
        async def classify(self, *args):
            return QuestionIntent(False, "aggregation", from_model=True, relational_query=plan)

    result = ask("Orders와 Customers를 Customer ID로 연결해서 Region이 North 또는 South인 매칭된 행의 Amount 합계",
                 summary, index, Classifier())
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"
