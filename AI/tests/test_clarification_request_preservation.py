import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.models import QuestionAnswerDraft
from app.agent.query.service import WorkbookQuestionService
from tests.support.clarification_fixtures import selection
from tests.test_clarification_metric_selection import MetricClassifier, report_fixture


class UnavailableGenerator:
    def __init__(self, original):
        self.original = original

    async def generate(self, question, *args):
        assert self.original in question
        return QuestionAnswerDraft(answer="요청한 조건까지 원본에서 확인할 수 없습니다.",
                                   evidence=[], confidence=0, limitations=["요청 전체를 확인하지 못했습니다."])


@pytest.mark.parametrize("question", [
    "2024년 9월 30일 Operating Income을 EUR로 환산해줘",
    "2024년 9월 30일 Operating Income 평균은?",
    "2024년 9월 30일 Operating Income 중 700 이상인 값만 알려줘",
    "2024년 9월 30일 Operating Income이 왜 이렇게 높아?",
])
def test_metric_source_choice_never_discards_conversion_aggregation_filter_or_interpretation(question):
    summary, index = report_fixture()
    query = WorkbookQuestionService(UnavailableGenerator(question), create_default_tool_registry(),
                                    classifier=MetricClassifier())
    original = asyncio.run(query.answer(question, summary, index))
    assert len(original.clarification_options) == 2
    for option in original.clarification_options:
        assert option.question.endswith(question)
        chosen = asyncio.run(query.answer(option.question, summary, index, selection(original, option)))
        assert chosen.verification.level != "request_checked"
        assert question in (chosen.resolved_question or chosen.question)
