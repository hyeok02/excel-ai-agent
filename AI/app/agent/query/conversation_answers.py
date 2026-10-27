"""Resolve referents separately, then run the normal source-verification pipeline."""
import asyncio

from app.agent.query.clarification_selection import answer_selected_source
from app.agent.query.conversation_choices import bound_choice_operation
from app.agent.query.conversation_checks import CONTEXT_CUE, resolution_is_safe, subject_only_followup
from app.agent.query.conversation_language import scope_only_followup, standalone_wording
from app.agent.query.conversation_periods import RELATIVE_YEAR, bound_relative_question
from app.agent.query.conversation_scopes import bound_scope_question
from app.agent.query.conversation_aggregate_conditions import SAME_CONDITIONS, bound_aggregate_conditions
from app.agent.query.conversation_sources import source_bound_context
from app.agent.query.source_lookup_answers import source_lookup_answer
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.models import (
    QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel,
)


async def answer_in_conversation(question, context, sources, resolver, answer_current):
    if context is not None and context.selection is not None:
        return await answer_selected_source(question, context.selection, sources, answer_current)
    standalone = standalone_wording(question)
    if (standalone != question.strip()
            and getattr(getattr(sources, "original_index", None), "source_provider", None) is not None):
        # A complete address-only request has no implicit subject to resolve.
        # The direct parser rejects leftover filters, pronouns and operations.
        direct = await asyncio.to_thread(source_lookup_answer, standalone, sources)
        if direct is not None:
            return direct.model_copy(update={"question": question})
    label_only = subject_only_followup(question, sources.index)
    depends_on_context = label_only or bool(CONTEXT_CUE.search(question) or RELATIVE_YEAR.search(question)
                                            or SAME_CONDITIONS.match(question.strip()))
    if context is None or not depends_on_context:
        return await answer_current(question, sources)
    unresolved_parent = bool(context.turns and context.turns[-1].needs_clarification)
    scope_selection = scope_only_followup(question, sources.index)
    if unresolved_parent and label_only and not scope_selection:
        return context_clarification(question)
    entries = await asyncio.to_thread(source_bound_context, context, sources.summary, sources.index)
    if not entries:
        if depends_on_context:
            return context_clarification(question)
        return await answer_current(question, sources)
    try:
        period_question = bound_relative_question(question, entries)
        draft = bound_choice_operation(question, context, entries, sources.summary)
        draft = draft or bound_scope_question(question, context, entries, sources.index)
        draft = draft or await asyncio.to_thread(bound_aggregate_conditions, question, context, entries,
                                                sources.summary, sources.index)
        if draft is None:
            if resolver is None:
                return context_clarification(question)
            draft = await resolver.resolve(period_question or question, entries)
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        if depends_on_context:
            return context_clarification(question)
        return await answer_current(question, sources)
    if draft.status == "standalone":
        if label_only or (RELATIVE_YEAR.search(question) and period_question is None):
            return context_clarification(question)
        if period_question:
            from app.agent.query.conversation_models import ContextResolutionDraft
            latest = max((entry for entry in entries if entry["id"].startswith("turn:")),
                         key=lambda entry: int(entry["id"].split(":")[1]))
            draft = ContextResolutionDraft(status="resolved", question=standalone_wording(period_question),
                                           context_ids=[latest["id"]])
        else:
            answer = await answer_current(standalone_wording(question), sources)
            return answer.model_copy(update={"question": question})
    if unresolved_parent and not scope_selection:
        return context_clarification(question)
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
        "question": question, "resolved_question": answer.resolved_question or draft.question,
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
