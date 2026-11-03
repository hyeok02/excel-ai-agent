"""Regression coverage for clarification selection and restored conversations."""
import asyncio

from app.agent.query.conversation_models import QuestionConversation
from tests.support.single_series_extreme_fixtures import asthma_source, question_service


QUESTION = "천식 유병률이 가장 많이 증가한 년도는 언제야?"


def _option(summary, index):
    ambiguous = asyncio.run(question_service().answer(QUESTION, summary, index))
    option = next(
        item for item in ambiguous.clarification_options
        if item.label == "Asthma Attack Prevalence"
    )
    return ambiguous, option


def test_clicked_source_choice_reenters_verified_calculator_through_service():
    summary, index = asthma_source()
    ambiguous, option = _option(summary, index)
    context = QuestionConversation(selection={
        "source_question": ambiguous.question,
        "option_id": option.id,
    })

    chosen = asyncio.run(question_service().answer(option.question, summary, index, context))

    assert chosen.status == "answered", chosen.model_dump()
    assert chosen.verification.level == "request_checked", chosen.model_dump()
    assert chosen.resolved_question == option.question
    assert "select_source_scope" in chosen.selected_tools
    assert "2022" in chosen.answer and "2021" in chosen.answer and "8.0%p" in chosen.answer


def test_stale_clicked_choice_is_revalidated_against_current_workbook():
    summary, index = asthma_source()
    ambiguous, option = _option(summary, index)
    context = QuestionConversation(selection={
        "source_question": ambiguous.question,
        "option_id": "0" * 64,
    })

    chosen = asyncio.run(question_service().answer(option.question, summary, index, context))

    assert chosen.status == "answered", chosen.model_dump()
    assert chosen.verification.level == "request_checked", chosen.model_dump()
    assert "clarification_scope_revalidated" in chosen.verification.checks
    assert "select_source_scope" in chosen.selected_tools
    assert "2022" in chosen.answer and "2021" in chosen.answer and "8.0%p" in chosen.answer


def test_scoped_choice_does_not_depend_on_the_saved_parent_question():
    summary, index = asthma_source()
    scoped = (
        "'Childhood Asthma'!A1:E4 범위의 Asthma Attack Prevalence 기준으로: "
        "천식 유병률이 가장 많이 증가한 년도는 언제야?"
    )
    context = QuestionConversation(selection={
        "source_question": "저장 당시의 다른 원래 질문",
        "option_id": "0" * 64,
    })

    chosen = asyncio.run(question_service().answer(scoped, summary, index, context))

    assert chosen.status == "answered", chosen.model_dump()
    assert chosen.verification.level == "request_checked", chosen.model_dump()
    assert "clarification_scope_revalidated" in chosen.verification.checks
    assert "2022" in chosen.answer and "2021" in chosen.answer and "8.0%p" in chosen.answer


def test_stale_choice_cannot_bypass_verification_with_an_unscoped_question():
    summary, index = asthma_source()
    context = QuestionConversation(selection={
        "source_question": QUESTION,
        "option_id": "0" * 64,
    })

    rejected = asyncio.run(
        question_service().answer("그냥 아무 숫자나 알려줘", summary, index, context)
    )

    assert rejected.status == "insufficient_evidence", rejected.model_dump()
    assert rejected.verification.level == "unverified", rejected.model_dump()
    assert not rejected.evidence
