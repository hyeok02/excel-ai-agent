"""Resolve referents separately, then run the normal source-verification pipeline."""
import asyncio

from app.agent.query.conversation_checks import CONTEXT_CUE, resolution_is_safe, subject_only_followup
from app.agent.query.conversation_sources import source_bound_context
from app.agent.query.models import (
    QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel,
)


async def answer_in_conversation(question, context, sources, resolver, answer_current):
    if context is None:
        return await answer_current(question, sources)
    entries = await asyncio.to_thread(source_bound_context, context, sources.summary, sources.index)
    label_only = subject_only_followup(question, sources.index)
    depends_on_context = label_only or bool(CONTEXT_CUE.search(question))
    if not entries or resolver is None:
        if depends_on_context:
            return context_clarification(question)
        return await answer_current(question, sources)
    try:
        draft = await resolver.resolve(question, entries)
    except Exception:
        if depends_on_context:
            return context_clarification(question)
        return await answer_current(question, sources)
    if draft.status == "standalone":
        if label_only:
            return context_clarification(question)
        return await answer_current(question, sources)
    # An unresolved latest turn must not disappear and silently reconnect "it"
    # to an older, successfully answered subject instead.
    if context.turns and f"turn:{len(context.turns) - 1}" not in {entry["id"] for entry in entries}:
        return context_clarification(question)
    if draft.status != "resolved" or not resolution_is_safe(question, draft, entries):
        return context_clarification(question)
    answer = await answer_current(draft.question, sources)
    if draft.question.strip() == question.strip():
        return answer
    # Source values were checked, but resolving a pronoun is a model inference,
    # not deterministic proof of the original user's intended scope.
    verification = answer.verification
    if verification.level != QuestionVerificationLevel.UNVERIFIED:
        verification = QuestionAnswerVerification(
            level=QuestionVerificationLevel.SOURCE_CHECKED,
            checks=[check for check in verification.checks if check != "request_alignment"]
            + ["context_resolved"],
        )
    return answer.model_copy(update={
        "question": question, "resolved_question": draft.question,
        "status": QuestionAnswerStatus.LIMITED if answer.status == "answered" else answer.status,
        "verification": verification,
        "confidence": min(answer.confidence, 0.8),
        "limitations": [*answer.limitations, "이전 맥락을 연결한 답변입니다. 표시된 해석 질문의 대상·조건을 확인해주세요."],
    })


def context_clarification(question: str) -> QuestionAnswer:
    return QuestionAnswer(
        question=question,
        answer="이전 맥락에서 가리키는 대상을 확정하지 못했습니다. 어떤 항목·시트·조건인지 알려주세요.",
        status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE, confidence=0,
        selected_tools=["clarify_question_context"], evidence=[],
        limitations=["이전 질문이나 인사이트의 표현을 원본 사실로 간주하지 않았습니다."],
    )
