"""A named subject alone must not silently replace an inherited metric with a row."""
import asyncio
from types import SimpleNamespace

import pytest

from app.agent.query.conversation_answers import answer_in_conversation
from app.agent.query.conversation_checks import subject_only_followup
from app.agent.query.conversation_models import ContextResolutionDraft, QuestionConversation
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from tests.tabular_query_fixtures import table_fixture


def fixture():
    summary, index = table_fixture([(1, 1, [
        ["장비", "검토 상태", "수량"], ["Unit-A", "x", 10],
        ["Unit-B", "o", 20], ["냉각 장치", "x", 30], ["North Wing", "o", 40],
    ])], "점검")
    context = QuestionConversation(turns=[{
        "question": "Unit-A의 수량은?", "evidence": ["점검!A1:C2"],
    }])
    return SimpleNamespace(summary=summary, index=index), context


class Resolver:
    def __init__(self, resolved=None):
        self.resolved, self.seen = resolved, []

    async def resolve(self, question, entries):
        self.seen = entries
        return ContextResolutionDraft(
            status="resolved" if self.resolved else "standalone",
            question=self.resolved, context_ids=["turn:0"] if self.resolved else [],
        )


def run_question(question, resolver, context=None):
    sources, previous = fixture()
    calls = []

    async def answer_current(current, source):
        calls.append(current)
        return QuestionAnswer(
            question=current, answer="20", status="answered", confidence=1,
            selected_tools=[], evidence=[], limitations=[],
            verification=QuestionAnswerVerification(
                level="request_checked", checks=["source_values", "request_alignment"],
            ),
        )

    answer = asyncio.run(answer_in_conversation(
        question, previous if context is None else context, sources, resolver, answer_current,
    ))
    return answer, calls


@pytest.mark.parametrize("question", [
    "그럼 Unit-B는?", "Unit-B는?", "그러면 냉각 장치는?", "냉각 장치도?",
    "그럼 North Wing은?", "What about North Wing?", "Then Unit-B?",
])
def test_source_label_only_is_elliptical_without_file_specific_vocabulary(question):
    sources, _ = fixture()
    assert subject_only_followup(question, sources.index)


@pytest.mark.parametrize("question", [
    "그럼 Unit-B의 수량은?", "냉각 장치의 검토 상태는?",
    "What is North Wing's 수량?", "그럼 점검!C3 값은?",
    "Unit-B의 모든 항목을 보여줘",
])
def test_complete_requests_are_not_label_only(question):
    sources, _ = fixture()
    assert not subject_only_followup(question, sources.index)


@pytest.mark.parametrize("question", ["그럼 Unit-B는?", "그러면 냉각 장치는?", "What about North Wing?"])
def test_standalone_misclassification_cannot_return_verified_whole_row(question):
    resolver = Resolver()
    answer, calls = run_question(question, resolver)
    assert answer.status == "insufficient_evidence"
    assert answer.verification.level == "unverified"
    assert answer.selected_tools == ["clarify_question_context"]
    assert answer.resolved_question is None
    assert calls == []
    # The new subject is outside the previous evidence range: detection must use
    # this workbook's full authorized index, not only the old turn's source hints.
    assert "Unit-B" not in str(resolver.seen)
    assert "North Wing" not in str(resolver.seen)


def test_complete_followup_standalone_still_runs_the_explicit_question():
    question = "그럼 Unit-B의 수량은?"
    answer, calls = run_question(question, Resolver())
    assert calls == [question]
    assert answer.status == "answered"
    assert answer.verification.level == "request_checked"
    assert answer.resolved_question is None


def test_elliptical_followup_can_resolve_and_recheck_inherited_metric():
    resolved = "Unit-B의 수량은?"
    answer, calls = run_question("그럼 Unit-B는?", Resolver(resolved))
    assert calls == [resolved]
    assert answer.question == "그럼 Unit-B는?"
    assert answer.resolved_question == resolved
    assert answer.answer == "20"
    assert answer.status == "limited"
    assert answer.verification.level == "source_checked"
    assert "context_resolved" in answer.verification.checks
    assert "request_alignment" not in answer.verification.checks
