"""Clarification picks source scope without losing the parent's requested table."""
import asyncio

import pytest

from app.agent.query.conversation_answers import answer_in_conversation
from app.agent.query.conversation_language import selected_scope_sheet
from app.agent.query.conversation_models import ContextResolutionDraft, ConversationTurn, QuestionConversation
from app.agent.query.models import QuestionAnswer
from tests.test_conversation_independent import fixture


class NoResolver:
    async def resolve(self, *_):
        raise AssertionError("Explicit sheet binding must not rely on a model rewrite")


def run(question, context, sources):
    calls = []

    async def current(value, _):
        calls.append(value)
        return QuestionAnswer(question=value, answer="source lookup", status="answered",
                              confidence=1, selected_tools=[], evidence=[], limitations=[])

    answer = asyncio.run(answer_in_conversation(question, context, sources, NoResolver(), current))
    return answer, calls


@pytest.mark.parametrize("needs_clarification", [False, True])
def test_scope_selection_preserves_parent_table_subject_and_filters(needs_clarification):
    sources, _ = fixture()
    previous = "TOP 25 EMPLOYERS에서 Nation-A의 2027년 정규직 직원 수는? 계약직은 제외해줘"
    context = QuestionConversation(turns=[{
        "question": previous, "evidence": ["Countries!A1:B3"],
        "needs_clarification": needs_clarification,
    }])
    answer, calls = run("Countries 시트 기준으로 알려줘", context, sources)
    assert calls == [f"Countries 시트에서 {previous}"]
    assert answer.resolved_question == calls[0]
    assert answer.status == "limited"


def test_unresolved_parent_does_not_allow_arbitrary_subject_switch():
    sources, _ = fixture()
    context = QuestionConversation(turns=[{
        "question": "직원 수는?", "evidence": ["Countries!A1:B3"],
        "needs_clarification": True,
    }])
    answer, calls = run("그럼 Nation-B는?", context, sources)
    assert calls == []
    assert answer.selected_tools == ["clarify_question_context"]


def test_independent_question_still_runs_after_unresolved_parent():
    sources, _ = fixture()
    context = QuestionConversation(turns=[{
        "question": "직원 수는?", "evidence": ["Countries!A1:B3"],
        "needs_clarification": True,
    }])
    question = "Countries 시트에서 Nation-A의 직원 수는?"
    _, calls = run(question, context, sources)
    assert calls == [question]


def test_discourse_leading_independent_question_can_follow_unresolved_parent():
    sources, _ = fixture()
    context = QuestionConversation(turns=[{
        "question": "직원 수는?", "evidence": ["Countries!A1:B3"],
        "needs_clarification": True,
    }])
    calls = []

    class Resolver:
        async def resolve(self, *_):
            return ContextResolutionDraft(status="standalone")

    async def current(question, _):
        calls.append(question)
        return QuestionAnswer(question=question, answer="107", status="answered", confidence=1,
                              selected_tools=[], evidence=[], limitations=[])

    question = "그럼 Countries 시트에서 Nation-A의 직원 수는?"
    answer = asyncio.run(answer_in_conversation(question, context, sources, Resolver(), current))
    assert calls == ["Countries 시트에서 Nation-A의 직원 수는?"]
    assert answer.question == question


def test_resolver_cannot_invent_scope_after_unresolved_parent():
    sources, _ = fixture()
    context = QuestionConversation(turns=[{
        "question": "직원 수는?", "evidence": ["Countries!A1:B3"],
        "needs_clarification": True,
    }])

    class Resolver:
        async def resolve(self, *_):
            return ContextResolutionDraft(status="resolved", context_ids=["turn:0"],
                                          question="Countries 시트에서 Nation-A의 직원 수는?")

    async def current(*_):
        raise AssertionError("An unresolved scope must not be inherited")

    answer = asyncio.run(answer_in_conversation("그중 직원 수는?", context, sources, Resolver(), current))
    assert answer.selected_tools == ["clarify_question_context"]


def test_latest_request_without_source_context_is_not_inherited():
    sources, _ = fixture()
    context = QuestionConversation(turns=[
        {"question": "Nation-A의 직원 수는?", "evidence": ["Countries!A1:B3"]},
        {"question": "Nation-B의 직원 수는?", "evidence": ["Missing!Z99"]},
    ])
    answer, calls = run("Countries 시트 기준으로 알려줘", context, sources)
    assert calls == []
    assert answer.selected_tools == ["clarify_question_context"]


def test_scope_selection_cannot_ignore_numbers_or_unknown_sheets():
    sources, _ = fixture()
    assert selected_scope_sheet("Countries 시트 기준으로 알려줘", sources.index) == "Countries"
    for question in ["Countries 2027년 기준으로 알려줘", "Missing 시트 기준으로 알려줘",
                     "Countries 7% 기준으로 알려줘", "Countries #12만 알려줘"]:
        assert selected_scope_sheet(question, sources.index) is None


def test_old_context_defaults_to_no_pending_clarification():
    turn = ConversationTurn(question="직원 수는?", evidence=[])
    assert turn.needs_clarification is False
