"""Q&A regressions using the exact facts emitted for diverse source shapes."""

from types import SimpleNamespace

from app.agent.query import verified_facts
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.verified_insight_answers import validated_verified_insight_answer
from app.services.insights.narratives.flag_narratives import flag_matrix_report
from app.services.insights.narratives.ranked_narratives import ranked_report
from app.services.insights.narratives.snapshot_narratives import snapshot_report
from app.services.insights.narratives.source_narratives import source_narrative_report
from app.services.insights.quality import build_source_report
from tests.support.diverse_question_contexts import (
    checklist_context,
    event_context,
    ownership_context,
    plain_record_context,
    sales_context,
    snapshot_context,
)
from tests.support.narrative_contexts import trend_context
from tests.support.verified_insight_execution import (
    answer_from_verified_report,
    execution_from_report,
)


def test_time_series_question_reuses_the_exact_trend_fact() -> None:
    context = trend_context()
    report = source_narrative_report(context)

    answer = answer_from_verified_report("전체 인원 추이가 어떻게 돼?", report, context)

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == report.insights[0].fact
    assert {item.reference for item in answer.evidence} >= {"A4", "B4", "A6", "B6"}


def test_sales_question_reuses_a_verified_financial_change() -> None:
    context = sales_context()
    report = source_narrative_report(context)

    answer = answer_from_verified_report("매출 추이 알려줘", report, context)

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == report.insights[0].fact
    assert "100USD" in answer.answer and "150USD" in answer.answer
    assert "50USD(50.00%) 증가" in answer.answer


def test_plain_record_question_reuses_a_verified_cell_lookup_fact() -> None:
    context = plain_record_context()
    report = build_source_report(context)

    answer = answer_from_verified_report("노트북 1월 값 알려줘", report, context)

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == report.insights[0].fact
    assert {item.reference for item in answer.evidence} == {"A2", "B2", "C2"}


def test_checklist_question_reuses_the_matching_column_fact() -> None:
    context = checklist_context()
    items, overview = flag_matrix_report(context)
    report = SimpleNamespace(insights=items, overview=overview)

    answer = answer_from_verified_report(
        "네트워크 안정 표시는 어떻게 돼?", report, context
    )

    expected = next(item for item in items if item.title == "네트워크 안정 표시")
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == expected.fact
    assert {item.reference for item in answer.evidence} >= {"D1", "D2", "D6"}


def test_snapshot_question_reuses_verified_financial_levels() -> None:
    context = snapshot_context()
    items, overview = snapshot_report(context)
    report = SimpleNamespace(insights=items, overview=overview)

    answer = answer_from_verified_report("시가총액과 총부채 수치 알려줘", report, context)

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == items[0].fact
    assert "1,018,667" in answer.answer and "67,095" in answer.answer


def test_ownership_question_understands_rank_and_share_wording() -> None:
    context = ownership_context()
    items, overview = ranked_report(context)
    report = SimpleNamespace(insights=items, overview=overview)

    answer = answer_from_verified_report("최대 주주와 지분율 알려줘", report, context)

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == items[0].fact
    assert "The Vanguard Group" in answer.answer and "9.44%" in answer.answer


def test_recent_event_question_reuses_the_actual_event_record() -> None:
    context = event_context()
    report = build_source_report(context)

    answer = answer_from_verified_report("가장 최근 이벤트가 뭐야?", report, context)

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert answer.answer == report.insights[0].fact
    assert "2025년 1월 3일" in answer.answer
    assert "Strategic Investment" in answer.answer


def test_verified_question_context_keeps_event_record_fallback(monkeypatch) -> None:
    context = event_context()
    monkeypatch.setattr(verified_facts, "_build_context", lambda _: context)

    result = verified_facts.build_verified_question_context(SimpleNamespace())

    assert result["insights"]
    assert result["insights"][0]["fact"] == build_source_report(context).insights[0].fact
    assert result["insights"][0]["support_references"] == [
        "events!a2", "events!b2", "events!c2",
    ]


def test_rank_one_fact_is_not_reused_for_a_second_rank_question() -> None:
    context = ownership_context()
    items, overview = ranked_report(context)
    report = SimpleNamespace(insights=items, overview=overview)

    answer = validated_verified_insight_answer(
        "2위 주주와 지분율은?", execution_from_report(report, context), False
    )

    assert answer is None


def test_change_fact_is_not_reused_for_an_unobserved_month() -> None:
    context = sales_context()
    report = source_narrative_report(context)

    answer = validated_verified_insight_answer(
        "2025년 2월 매출은?", execution_from_report(report, context), False
    )

    assert answer is None
