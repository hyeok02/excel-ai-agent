"""Offline provider errors must not be presented as ambiguous workbook questions."""
import asyncio

import httpx
import pytest
from openai import RateLimitError

from app.agent.query.conversation_answers import answer_in_conversation
from app.agent.query.conversation_models import QuestionConversation
from app.agent.query.intent_classifier import LangChainQuestionIntentClassifier
from app.agent.query.quota_errors import QUOTA_MESSAGE, QuestionQuotaExhaustedError, raise_for_quota_exhaustion
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.tabular_source_alias_resolution import resolved_source_label_alias_answer
from tests.test_conversation_independent import fixture
from tests.test_tabular_source_alias_resolution import _untranslated


def quota_error(code):
    response = httpx.Response(429, request=httpx.Request("POST", "https://provider.invalid"))
    return RateLimitError("provider-private-message", response=response,
                          body={"error": {"code": code, "type": "insufficient_quota"}})


async def run_layer(layer, error):
    class Failing:
        async def resolve(self, *_):
            raise error
        async def classify(self, *_):
            raise error
        async def ainvoke(self, *_):
            raise error

    sources, _ = fixture()
    if layer == "context":
        context = QuestionConversation(turns=[{
            "question": "직원 수는?", "evidence": ["Countries!A1:B3"],
        }])
        return await answer_in_conversation("그중 직원 수는?", context, sources, Failing(), None)
    if layer == "classifier":
        classifier = LangChainQuestionIntentClassifier("unused", "unused", 1)
        classifier._build_model = lambda: Failing()
        return await classifier.classify("직원 수는?", sources.summary)
    if layer == "service":
        return await WorkbookQuestionService(None, None, classifier=Failing())._question_intent(
            "직원 수는?", sources.summary)
    return await resolved_source_label_alias_answer(*_untranslated(), resolver=Failing())


@pytest.mark.parametrize("layer", ["context", "classifier", "service", "alias"])
@pytest.mark.parametrize("code", ["credit_balance_exhausted", "insufficient_quota"])
def test_exhausted_quota_propagates_as_safe_generation_error(layer, code):
    with pytest.raises(QuestionQuotaExhaustedError) as caught:
        asyncio.run(run_layer(layer, quota_error(code)))
    assert str(caught.value) == QUOTA_MESSAGE
    assert "provider-private-message" not in str(caught.value)


@pytest.mark.parametrize("layer", ["context", "classifier", "service", "alias"])
def test_transient_failure_keeps_existing_fallback(layer):
    answer = asyncio.run(run_layer(layer, TimeoutError("temporary")))
    if layer == "context":
        assert answer.selected_tools == ["clarify_question_context"]
    elif layer in {"classifier", "service"}:
        assert answer.from_model is False
    else:
        assert answer is None


def test_safe_error_is_not_swallowed_again_by_service():
    with pytest.raises(QuestionQuotaExhaustedError, match="AI 서비스 사용 한도"):
        asyncio.run(run_layer("service", QuestionQuotaExhaustedError()))


def test_ordinary_rate_limit_or_message_text_is_not_exhausted_quota():
    response = httpx.Response(429, request=httpx.Request("POST", "https://provider.invalid"))
    ordinary = RateLimitError("try later", response=response, body={"code": "rate_limit_exceeded"})
    assert raise_for_quota_exhaustion(ordinary) is None
    assert raise_for_quota_exhaustion(RuntimeError("insufficient_quota in untrusted text")) is None
