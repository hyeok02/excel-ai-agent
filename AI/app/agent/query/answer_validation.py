from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.answer_grounding import (
    answer_is_grounded,
    verified_fallback_answer,
    verified_support_references,
)
from app.agent.query.claim_bindings import answer_bindings_supported
from app.agent.query.comparison_answers import validated_comparison_answer
from app.agent.query.comparison_evidence import available_evidence as _available_evidence
from app.agent.query.models import (
    QuestionAnswer,
    QuestionAnswerDraft,
    QuestionAnswerEvidence,
    QuestionAnswerStatus,
)
from app.agent.query.numeric_support import (
    answer_units_supported,
    supported_answer_numbers,
)
from app.agent.query.references import matching_references, normalize_reference
from app.services.insights.verification.numeric_validation import unmatched_numbers


def validate_answer(
    question: str,
    draft: QuestionAnswerDraft,
    execution: AgentExecution,
    index_truncated: bool,
) -> QuestionAnswer:
    available = _available_evidence(execution)
    if canonical := validated_comparison_answer(
        question, execution, index_truncated, available
    ):
        return canonical
    matched, unknown = _match_evidence(draft.evidence, available)
    support = verified_support_references(question, matched, execution)
    supported_evidence, _ = _match_evidence(support, available)
    matched.extend(item for item in supported_evidence if item not in matched)
    limitations = list(draft.limitations)
    if unknown:
        limitations.append("AI가 제시한 일부 셀 주소를 Tool 근거에서 확인하지 못했습니다.")
    if index_truncated:
        limitations.append("대용량 워크북의 일부 셀은 검색 범위에서 제외되었습니다.")
    failed = any(step.status is AgentStepStatus.FAILED for step in execution.steps)
    if failed:
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    if not matched:
        return _blocked(
            question,
            execution,
            [],
            limitations or ["질문과 직접 연결되는 셀 근거가 없습니다."],
            "현재 확인된 원본 셀 근거만으로는 이 질문에 답할 수 없습니다.",
        )
    candidates = supported_answer_numbers(question, matched, execution)
    answer = draft.answer
    number_error = bool(unmatched_numbers(answer, candidates))
    unit_error = not answer_units_supported(answer, matched, execution)
    meaning_error = not answer_is_grounded(
        answer, matched, execution, question
    ) or not answer_bindings_supported(answer, matched)
    if number_error or unit_error or meaning_error:
        answer = verified_fallback_answer(question, matched, execution) or ""
        if not answer:
            if number_error:
                limitations.append("답변의 일부 수치를 원본 셀이나 검증된 계산에서 확인하지 못했습니다.")
            if unit_error:
                limitations.append("답변의 백분율 단위를 원본 셀이나 검증된 계산에서 확인하지 못했습니다.")
            if meaning_error:
                limitations.append("답변의 일부 의미를 인용한 원본에서 확인하지 못했습니다.")
            return _blocked(
                question, execution, matched, limitations,
                "답변 내용을 원본 셀과 대조하지 못해 결과를 표시하지 않았습니다.",
            )
    verification_limited = bool(unknown or failed)
    limited = verification_limited or index_truncated
    return QuestionAnswer(
        question=question,
        answer=answer,
        status=QuestionAnswerStatus.LIMITED if limited else QuestionAnswerStatus.ANSWERED,
        confidence=min(draft.confidence, 0.7) if verification_limited else draft.confidence,
        selected_tools=_tools(execution),
        evidence=[_present(item) for item in matched],
        limitations=_unique(limitations),
    )


def _match_evidence(citations, available):
    matched_keys, unknown = [], []
    keys = set(available)
    for citation in citations:
        normalized = normalize_reference(citation)
        resolved = matching_references(normalized, keys) if normalized else set()
        if not resolved:
            unknown.append(str(citation))
            continue
        matched_keys.extend(key for key in available if key in resolved)
    return [available[key] for key in dict.fromkeys(matched_keys)], unknown


def _blocked(question, execution, evidence, limitations, answer):
    return QuestionAnswer(
        question=question,
        answer=answer,
        status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE,
        confidence=0,
        selected_tools=_tools(execution),
        evidence=[_present(item) for item in evidence],
        limitations=_unique(limitations),
    )


def _present(item) -> QuestionAnswerEvidence:
    content = item.formula or (str(item.value) if item.value is not None else "")
    label = f"{item.description}: {content}" if content else item.description
    return QuestionAnswerEvidence(**item.model_dump(), label=label[:160])


def _tools(execution):
    return [step.tool_name for step in execution.steps]


def _unique(items):
    return list(dict.fromkeys(items))
