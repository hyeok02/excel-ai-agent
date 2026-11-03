"""Validate a clicked option against current sources before any model call."""
import asyncio
from hmac import compare_digest

from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.clarification_table_options import named_table_option
from app.agent.query.models import (
    QuestionAnswer,
    QuestionAnswerStatus,
    QuestionVerificationLevel,
)
from app.agent.query.time_series_answers import time_series_answer


async def answer_selected_source(question, selection, sources, answer_current):
    # A clicked option already carries the selected sheet/range/metric in its
    # canonical question.  Execute that current-workbook scope first instead of
    # making a valid answer depend on a previously persisted option id or its
    # source question.  We only accept a deterministic, evidence-backed result,
    # so an arbitrary or stale client question still cannot gain verification.
    revalidated = await asyncio.to_thread(
        time_series_answer, question, sources.summary, sources.index,
    )
    if _is_fully_revalidated(revalidated):
        return _mark_revalidated_selection(revalidated, question)

    current = await asyncio.to_thread(
        time_series_answer, selection.source_question, sources.summary, sources.index,
    )
    if current is None:
        current = await asyncio.to_thread(
            ambiguous_source_answer, selection.source_question, sources.summary, sources.index,
        )
    option = next((option for option in current.clarification_options
                   if compare_digest(option.id, selection.option_id)
                   and option.question == question), None) if current else None
    if option is None:
        # A plan-scoped clarification (another table could run the same plan) is
        # not reproducible without the model; its option still names its own
        # table, so rebuild that table's candidates and match the bound identifier.
        option = await asyncio.to_thread(named_table_option, question, selection, sources)
    if option is None:
        # Persisted conversations can outlive the code or source-normalization
        # version that produced an option id.  The clicked question already
        # carries the chosen sheet/range/metric, so recover only when the current
        # workbook can deterministically execute and fully verify that exact
        # scoped question.  This keeps stale ids from blocking a valid choice
        # without allowing an unverified or model-generated answer through.
        return invalid_selection_answer(question)
    answer = await answer_current(option.question, sources)
    return answer.model_copy(update={
        "resolved_question": answer.resolved_question or option.question,
        "selected_tools": list(dict.fromkeys(["select_source_scope", *answer.selected_tools])),
    })


def _is_fully_revalidated(answer):
    return bool(
        answer is not None
        and answer.status == QuestionAnswerStatus.ANSWERED
        and answer.verification.level == QuestionVerificationLevel.REQUEST_CHECKED
        and answer.evidence
    )


def _mark_revalidated_selection(answer, question):
    return answer.model_copy(update={
        "resolved_question": answer.resolved_question or question,
        "selected_tools": list(dict.fromkeys([
            "select_source_scope", *answer.selected_tools,
        ])),
        "verification": answer.verification.model_copy(update={
            "checks": list(dict.fromkeys([
                *answer.verification.checks,
                "clarification_scope_revalidated",
            ])),
        }),
    })


def invalid_selection_answer(question):
    return QuestionAnswer(
        question=question, answer="선택한 후보를 현재 파일과 질문에서 다시 확인하지 못했습니다. 원래 질문을 다시 보내 후보를 선택해 주세요.",
        status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE, confidence=0,
        selected_tools=["clarify_source_scope"], evidence=[],
        limitations=["파일·분석 범위·원래 질문 또는 선택 항목이 바뀐 경우 이전 후보를 사용할 수 없습니다."],
    )
