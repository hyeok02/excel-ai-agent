import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.relational_routing import missing_relational_plan_answer
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.relational_query_fixtures import relational_fixture, relational_plan
from tests.test_relational_integration import NoGenerator


@pytest.mark.parametrize("question", [
    "Orders와 Customers를 연결해서 Amount 합계",
    "Join Orders and Customers and sum Amount",
    "Orders와 Customers를 Customer ID로 매칭한 Amount 합계",
])
def test_explicit_two_source_join_without_a_plan_never_returns_one_source_total(question):
    summary, _ = relational_fixture()
    result = missing_relational_plan_answer(question, summary, QuestionIntent(False, "aggregation"))
    assert result.status == "insufficient_evidence"
    assert "연결 키" in result.answer and "한 표의 값으로 대신" in result.answer
    assert result.verification.level == "unverified"


def test_period_comparison_and_single_source_word_match_are_not_join_requests():
    summary, _ = relational_fixture()
    assert missing_relational_plan_answer("Orders와 Customers의 전년 대비 Amount를 비교해줘", summary) is None
    assert missing_relational_plan_answer("Orders를 연결해서 Amount 확인", summary) is None


def test_valid_relational_plan_is_not_blocked_by_missing_plan_guard():
    summary, _ = relational_fixture()
    intent = QuestionIntent(False, "aggregation", relational_query=relational_plan(summary))
    assert missing_relational_plan_answer("Orders와 Customers 연결해서 합계", summary, intent) is None


@pytest.mark.parametrize("has_wrong_single_table_plan", [False, True])
def test_service_does_not_fall_back_to_one_table_after_join_classifier_failure(has_wrong_single_table_plan):
    summary, index = relational_fixture()

    class Classifier:
        async def classify(self, question, summary):
            if not has_wrong_single_table_plan:
                raise RuntimeError("model unavailable")
            plan = TabularQueryPlan(operation="numeric_summary", table_id="Orders!A1:C3", column_ids=["C"], statistic="sum")
            return QuestionIntent(False, "aggregation", (), True, plan)

    service = WorkbookQuestionService(NoGenerator(), create_default_tool_registry(), classifier=Classifier())
    result = asyncio.run(service.answer("Orders와 Customers를 연결해서 Amount 합계", summary, index))
    assert result.status == "insufficient_evidence", result.answer
    assert "한 표의 값으로 대신" in result.answer
    assert result.verification.level == "unverified"
