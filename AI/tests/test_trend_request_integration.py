"""Request scope survives deterministic routing and explicit UI source choices."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.conversation_models import QuestionConversation
from app.agent.query.service import WorkbookQuestionService
from tests.support.large_workbook_fixtures import offline, NoGeneratedAnswer, ForbiddenExternalCall
from tests.support.trend_adversarial_fixtures import direct, source, QUESTION
from tests.tabular_query_fixtures import table_fixture


class NoClassifier:
    async def classify(self, *args):
        raise ForbiddenExternalCall("A source-bound trend needs no model classifier")


def service():
    return WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry(), classifier=NoClassifier())


def test_source_trend_answers_before_classifier_or_generator():
    summary, index = source()
    answer = asyncio.run(service().answer(QUESTION, summary, index))
    assert answer.status == "answered" and "반등" in answer.answer
    assert "request_alignment" in answer.verification.checks


def test_known_source_translation_does_not_select_generic_total_descriptor():
    summary, index = table_fixture([(1, 1, [
        ["Date", "Services", "Total Employees"], ["2024-01-01", 50, 500],
        ["2024-02-01", 40, 600], ["2024-03-01", 45, 650],
    ])])
    answer = direct(summary, index, "서비스 부서 인원의 기간별 추이를 설명해줘")
    assert answer.status == "limited"  # A department name alone does not prove its unit.
    assert "Services" in answer.answer and "반등" in answer.answer
    assert "Total Employees" not in answer.answer and "650" not in answer.answer


@pytest.mark.parametrize("question", ["전체 직원 수의 월별 추이", "전체 직원 수의 연도별 추이"])
def test_wrong_cadence_is_not_a_verified_source_trend(question):
    summary, index = source()
    assert direct(summary, index, question).verification.level != "request_checked"


def test_existing_quarterly_observations_need_no_resampling():
    summary, index = source()
    answer = direct(summary, index, "전체 직원 수의 분기별 추이를 설명해줘")
    assert answer.status == "answered"


def test_calendar_year_window_preserves_intermediate_periods():
    summary, index = source()
    answer = direct(summary, index, "2024년 전체 직원 수의 기간별 추이를 설명해줘")
    assert answer.status == "answered" and "반등" in answer.answer


def test_ambiguous_trend_choice_revalidates_before_answering():
    first = [["Date", "Total Employees"], ["2024-01-01", 10], ["2024-02-01", 12]]
    second = [["Date", "Total Employees"], ["2024-01-01", 30], ["2024-02-01", 20]]
    summary, index = table_fixture([(1, 1, first), (8, 1, second)])
    answer = direct(summary, index)
    assert answer.status == "insufficient_evidence" and len(answer.clarification_options) == 2
    option = answer.clarification_options[0]
    context = QuestionConversation(selection={"source_question": QUESTION, "option_id": option.id})
    chosen = asyncio.run(service().answer(option.question, summary, index, context))
    assert chosen.status == "answered", chosen.model_dump()
    assert chosen.verification.level == "request_checked"
    assert "select_source_scope" in chosen.selected_tools


def test_ambiguous_other_date_axis_does_not_grant_full_request_badge():
    first = [["Date", "Total Employees"], ["2024-01-01", 10], ["2024-02-01", 12]]
    other = [["Date", "Total Employees", "Effective Date"],
             ["2024-01-01", 30, "2023-01-01"], ["2024-02-01", 20, "2023-02-01"]]
    summary, index = table_fixture([(1, 1, first), (8, 1, other)])
    answer = direct(summary, index)
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert "request_alignment" not in answer.verification.checks
    assert answer.clarification_options
