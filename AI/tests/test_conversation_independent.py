"""Context presence must not override an independently specified question."""
import asyncio
from types import SimpleNamespace

import pytest

from app.agent.query.conversation_answers import answer_in_conversation
from app.agent.query.conversation_models import ContextResolutionDraft, QuestionConversation
from app.agent.query.models import QuestionAnswer
from tests.tabular_query_fixtures import table_fixture


def fixture():
    summary, index = table_fixture([(1, 1, [
        ["Country", "Employees"], ["Nation-A", 107], ["Nation-B", 29],
    ])], "Countries")
    context = QuestionConversation(insights=[{
        "title": "직원 현황", "evidence": ["Countries!A1:B2"],
    }])
    return SimpleNamespace(summary=summary, index=index), context


@pytest.mark.parametrize("question", [
    "Nation-A의 직원 수는 몇 명이야?", "Countries 시트의 직원 수 합계는?",
    "2027년 예상 매출은?", "Country 열과 Employees 열의 차이를 알려줘",
])
def test_explicit_question_bypasses_unrelated_context_and_resolver(question):
    sources, context = fixture()
    calls = []

    class Resolver:
        async def resolve(self, *_):
            raise AssertionError("An independent question does not need a context model")

    async def current(value, _):
        calls.append(value)
        return QuestionAnswer(question=value, answer="107", status="answered", confidence=1,
                              selected_tools=[], evidence=[], limitations=[])

    answer = asyncio.run(answer_in_conversation(question, context, sources, Resolver(), current))
    assert calls == [question]
    assert answer.status == "answered"


def test_scope_selection_is_resolved_as_a_followup_not_a_new_question():
    sources, _ = fixture()
    context = QuestionConversation(turns=[{
        "question": "Nation-A의 직원 수는?", "evidence": ["Countries!A1:B3"],
    }])
    calls = []

    class Resolver:
        async def resolve(self, *_):
            return ContextResolutionDraft(status="resolved", context_ids=["turn:0"],
                                          question="Countries 시트에서 Nation-A의 직원 수는?")

    async def current(question, _):
        calls.append(question)
        return QuestionAnswer(question=question, answer="107", status="answered", confidence=1,
                              selected_tools=[], evidence=[], limitations=[])

    answer = asyncio.run(answer_in_conversation(
        "Countries 시트 기준으로 알려줘", context, sources, Resolver(), current))
    assert calls == ["Countries 시트에서 Nation-A의 직원 수는?"]
    assert answer.resolved_question == calls[0]


def test_bare_new_subject_in_another_language_cannot_pass_as_standalone():
    sources, context = fixture()

    class Resolver:
        async def resolve(self, *_):
            return ContextResolutionDraft(status="standalone")

    async def current(*_):
        raise AssertionError("A subject-only question still needs the previous metric")

    answer = asyncio.run(answer_in_conversation("다른나라은?", context, sources, Resolver(), current))
    assert answer.selected_tools == ["clarify_question_context"]
