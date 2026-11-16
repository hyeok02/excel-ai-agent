"""A trend stage that only failed to bind its series lets later stages answer; its refusal stays the fallback."""
import asyncio
from types import SimpleNamespace

from app.agent.query import query_replanning, time_series_answers
from app.agent.query.models import QuestionAnswer
from app.agent.query.series_binding import unbound


def _refusal(text, mark):
    answer = QuestionAnswer(question="q", answer=text, status="insufficient_evidence", confidence=0,
                            selected_tools=["chronological_trend"], evidence=[], limitations=[text])
    return unbound(answer) if mark else answer


def test_only_an_unbound_refusal_is_passed_on(monkeypatch):
    monkeypatch.setattr(time_series_answers, "series_attempt", lambda *args: _refusal("연결하지 못했습니다", True))
    assert time_series_answers.time_series_answer("q", None, None) is None
    fact = _refusal("같은 날짜에 서로 다른 값이 있습니다", False)
    monkeypatch.setattr(time_series_answers, "series_attempt", lambda *args: fact)
    assert time_series_answers.time_series_answer("q", None, None) is fact


def test_the_unbound_refusal_returns_when_later_stages_cannot_answer(monkeypatch):
    refusal, later = _refusal("연결하지 못했습니다", True), _refusal("답변이 없습니다", False)
    sources = SimpleNamespace(summary=None, index=None)

    async def answer(*args, **kwargs):
        return later
    monkeypatch.setattr(query_replanning, "_answer_with_replanning", answer)
    monkeypatch.setattr(query_replanning, "series_attempt", lambda *args: refusal)
    monkeypatch.setattr(query_replanning, "settled_answer", lambda question, sources, found: found)
    assert asyncio.run(query_replanning.answer_with_replanning(None, "q", sources)) is refusal
    answered = later.model_copy(update={"status": "limited", "answer": "GPT 답변"})

    async def drafted(*args, **kwargs):
        return answered
    monkeypatch.setattr(query_replanning, "_answer_with_replanning", drafted)
    assert asyncio.run(query_replanning.answer_with_replanning(None, "q", sources)) is answered
