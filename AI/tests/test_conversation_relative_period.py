import asyncio
from types import SimpleNamespace

import pytest

from app.agent.query.conversation_answers import answer_in_conversation
from app.agent.query.conversation_models import ContextResolutionDraft, QuestionConversation
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("mode", ["standalone", "resolved"])
def test_corroborated_relative_date_reaches_lookup_without_changed_period_or_grain(mode):
    summary, index = table_fixture([(1, 1, [
        ["Date", "Period", "Profit"],
        ["2026-01-31T00:00:00", "Quarter", 40],
        ["2025-01-31T00:00:00", "Quarter", 50],
    ])], "Results")
    sources = SimpleNamespace(summary=summary, index=index)
    context = QuestionConversation(turns=[{
        "question": "Results 시트의 2026년 1월 31일 분기 순이익은?",
        "evidence": ["Results!A1:C2"],
    }])
    calls, seen = [], []

    class Resolver:
        async def resolve(self, question, _):
            seen.append(question)
            return ContextResolutionDraft(status=mode, question=question if mode == "resolved" else None,
                                          context_ids=["turn:0"] if mode == "resolved" else [])

    async def current(question, _):
        calls.append(question)
        return QuestionAnswer(question=question, answer="50", status="answered", confidence=1,
                              selected_tools=[], evidence=[], limitations=[],
                              verification=QuestionAnswerVerification(level="request_checked", checks=["metric"]))

    original = "그럼 전년도 같은 분기 순이익은?"
    answer = asyncio.run(answer_in_conversation(original, context, sources, Resolver(), current))
    assert seen == ["Results 시트에서 2025년 1월 31일 분기 순이익은?"]
    assert calls == seen
    assert answer.question == original
    assert answer.resolved_question == calls[0]
    assert answer.status == "limited"
    assert answer.verification.level == "source_checked"


def test_period_normalization_never_invents_a_date_without_source_corroboration():
    from app.agent.query.conversation_periods import bound_relative_question

    context = [{"id": "turn:0", "hint": {"question": "2026년 1월 31일 순이익은?"},
                "source_cells": [{"reference": "Results!A1", "value": "2025-01-31T00:00:00"}]}]
    assert bound_relative_question("전년도 같은 분기 순이익은?", context) is None
