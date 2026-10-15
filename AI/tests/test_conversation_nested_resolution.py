"""Keep the final source-bound execution question through context wrapping."""
import asyncio
from types import SimpleNamespace

import pytest

from app.agent.query.conversation_answers import answer_in_conversation
from app.agent.query.conversation_models import ContextResolutionDraft, QuestionConversation
from app.agent.query.models import QuestionAnswer
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("inner_question,inner_check", [
    ("Inventory 시트에서 수량이 20 이상인 항목 중 변경점에 '신규'가 포함된 항목만 보여줘",
     "partial_category_resolved"),
    ("Inventory 시트에서 수량이 20 이상인 항목 중 변경점이 신규(New)인 항목만 보여줘",
     "semantic_alias_resolved"),
    (None, "request_alignment"),
])
def test_nested_source_rewrite_survives_outer_context_resolution(inner_question, inner_check):
    summary, index = table_fixture([(1, 1, [
        ["항목", "수량", "변경점"], ["Unit-A", 30, "신규 작업"], ["Unit-B", 10, "기존"],
    ])], "Inventory")
    sources = SimpleNamespace(summary=summary, index=index)
    context = QuestionConversation(turns=[{
        "question": "Inventory 시트에서 수량이 20 이상인 항목만 보여줘",
        "evidence": ["Inventory!A1:C3"],
    }])
    original = "그중 변경점이 신규인 항목만 보여줘"
    draft_question = "Inventory 시트에서 수량이 20 이상인 항목 중 변경점이 신규인 항목만 보여줘"
    calls = []

    class Resolver:
        async def resolve(self, *_):
            return ContextResolutionDraft(status="resolved", question=draft_question,
                                          context_ids=["turn:0"])

    async def current(question, _):
        calls.append(question)
        return QuestionAnswer(
            question=question, resolved_question=inner_question, answer="Unit-A: 30",
            status="answered", confidence=1, selected_tools=["tabular_query"],
            evidence=[], limitations=[], verification={
                "level": "source_checked" if inner_question else "request_checked",
                "checks": ["source_values", "table_scope", inner_check],
            },
        )

    answer = asyncio.run(answer_in_conversation(original, context, sources, Resolver(), current))
    assert calls == [draft_question]
    assert answer.question == original
    assert answer.resolved_question == (inner_question or draft_question)
    assert "20 이상" in answer.resolved_question
    assert "변경점" in answer.resolved_question
    assert answer.status == "limited"
    assert answer.confidence == 0.8
    assert answer.verification.level == "source_checked"
    assert "context_resolved" in answer.verification.checks
    assert "request_alignment" not in answer.verification.checks
    if inner_question:
        assert inner_check in answer.verification.checks
