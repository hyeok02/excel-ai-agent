import asyncio

import pytest

from app.agent.query.conversation_models import ContextResolutionDraft, QuestionConversation
from app.agent.query.models import QuestionAnswer
from app.agent.query.tabular_catalog import build_query_tables
from tests.support.clarification_fixtures import fixture, initial, QueryClassifier, selection, service


class Resolver:
    def __init__(self, resolved=None):
        self.resolved, self.calls = resolved, []

    async def resolve(self, question, context):
        self.calls.append((question, context))
        return ContextResolutionDraft(status="resolved" if self.resolved else "ambiguous",
                                      question=self.resolved, context_ids=["turn:0"] if self.resolved else [])


def selected_history(summary, index):
    initial_answer = initial(summary, index)
    option = initial_answer.clarification_options[1]
    classifier = QueryClassifier(build_query_tables(summary)[0], "C")
    chosen = asyncio.run(service(classifier).answer(
        option.question, summary, index, selection(initial_answer, option),
    ))
    restored = QuestionAnswer.model_validate_json(chosen.model_dump_json())
    return QuestionConversation.model_validate_json(QuestionConversation(turns=[{
        "question": restored.resolved_question or restored.question,
        "evidence": [f"{item.sheet_name}!{item.reference}" for item in restored.evidence][:12],
    }]).model_dump_json())


@pytest.mark.parametrize("followup", ["그 항목 평균은?", "그럼 그 항목 평균 알려줘", "what is the average of that field?"])
def test_clicked_currency_year_selection_survives_history_and_operation_followup(followup):
    summary, index = fixture()
    context = selected_history(summary, index)
    classifier = QueryClassifier(build_query_tables(summary)[0], "C", "average")
    result = asyncio.run(service(classifier).answer(followup, summary, index, context))
    assert "150" in result.answer
    assert "EUR" in result.resolved_question and "2025" in result.resolved_question
    assert "평균" in result.resolved_question
    assert result.verification.level == "source_checked"
    assert "context_resolved" in result.verification.checks
    assert result.question == followup


@pytest.mark.parametrize("followup", ["그럼 2026년 평균은?", "그럼 EUR 말고 USD 합계", "그럼 다른 항목 평균은?"])
def test_changed_year_currency_or_subject_is_not_attached_to_selected_scope(followup):
    summary, index = fixture()
    context = selected_history(summary, index)
    resolver = Resolver()
    result = asyncio.run(service(resolver=resolver).answer(followup, summary, index, context))
    assert len(resolver.calls) == 1
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"


def test_independent_question_does_not_inherit_selected_currency():
    summary, index = fixture()
    context = selected_history(summary, index)
    classifier = QueryClassifier(build_query_tables(summary)[0], "B")
    result = asyncio.run(service(classifier).answer("Revenue (USD) (2025) 합계는?", summary, index, context))
    assert result.status == "answered" and "합계 30" in result.answer
    assert result.resolved_question is None
    assert result.verification.level == "request_checked"


def test_context_resolved_ambiguity_binds_options_to_resolved_not_ellipsis_question():
    summary, index = fixture()
    resolved = "North America 시트 Revenue 합계는?"
    context = QuestionConversation(turns=[{
        "question": "Revenue 합계는?", "evidence": ["North America!B1:C3"],
    }])
    classifier = QueryClassifier(build_query_tables(summary)[0], "C")
    ambiguous = asyncio.run(service(classifier, Resolver(resolved)).answer(
        "그 항목 합계는?", summary, index, context,
    ))
    assert ambiguous.resolved_question == resolved
    assert len(ambiguous.clarification_options) == 2
    option = ambiguous.clarification_options[1]
    picked = asyncio.run(service(classifier).answer(option.question, summary, index, selection(ambiguous, option)))
    assert "300" in picked.answer and picked.verification.level == "request_checked"
    bad_context = selection(ambiguous, option)
    bad_context.selection.source_question = ambiguous.question
    rejected = asyncio.run(service().answer(option.question, summary, index, bad_context))
    assert rejected.status == "insufficient_evidence" and rejected.evidence == []
