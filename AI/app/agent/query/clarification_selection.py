"""Validate a clicked option against current sources before any model call."""
import asyncio
from hmac import compare_digest

from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus


async def answer_selected_source(question, selection, sources, answer_current):
    current = await asyncio.to_thread(
        ambiguous_source_answer, selection.source_question, sources.summary, sources.index,
    )
    option = next((option for option in current.clarification_options
                   if compare_digest(option.id, selection.option_id)
                   and option.question == question), None) if current else None
    if option is None:
        return invalid_selection_answer(question)
    answer = await answer_current(option.question, sources)
    return answer.model_copy(update={
        "resolved_question": answer.resolved_question or option.question,
        "selected_tools": list(dict.fromkeys(["select_source_scope", *answer.selected_tools])),
    })


def invalid_selection_answer(question):
    return QuestionAnswer(
        question=question, answer="선택한 후보를 현재 파일과 질문에서 다시 확인하지 못했습니다. 원래 질문을 다시 보내 후보를 선택해 주세요.",
        status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE, confidence=0,
        selected_tools=["clarify_source_scope"], evidence=[],
        limitations=["파일·분석 범위·원래 질문 또는 선택 항목이 바뀐 경우 이전 후보를 사용할 수 없습니다."],
    )
