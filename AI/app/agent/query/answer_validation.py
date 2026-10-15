from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.answer_clauses import clauses, supported_clauses
from app.agent.query.answer_grounding import (
    answer_is_grounded,
    verified_fallback_answer,
    verified_support_references,
)
from app.agent.query.change_direction import answer_directions_supported
from app.agent.query.claim_bindings import answer_bindings_supported
from app.agent.query.comparison_answers import validated_comparison_answer
from app.agent.query.comparison_evidence import available_evidence as _available_evidence
from app.agent.query.models import (
    QuestionAnswer, QuestionAnswerDraft, QuestionAnswerEvidence, QuestionAnswerStatus,
)
from app.agent.query.numeric_support import answer_units_supported, supported_answer_numbers
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
    answer = draft.answer
    def _failures(part: str) -> tuple[bool, bool, bool, bool, bool]:
        # 전체로 보면 한 절의 근거가 다른 절의 주장을 통과시킨다.
        number = bool(
            unmatched_numbers(
                part, supported_answer_numbers(question, matched, execution, part)
            )
        )
        unit = not answer_units_supported(part, matched, execution)
        meaning = not answer_is_grounded(part, matched, execution, question)
        binding = not answer_bindings_supported(part, matched)
        direction = not answer_directions_supported(part, matched)
        return number, unit, meaning, binding, direction

    parts = clauses(answer) or [answer]
    failures = [_failures(part) for part in parts]
    number_error = any(item[0] for item in failures)
    unit_error = any(item[1] for item in failures)
    meaning_error = any(item[2] for item in failures)
    binding_error = any(item[3] for item in failures)
    direction_error = any(item[4] for item in failures)
    verified_parts = {part for part, errors in zip(parts, failures) if not any(errors)}
    answer, trimmed = supported_clauses(
        answer, verified_parts.__contains__
    ) if any(any(item) for item in failures) else (answer, False)
    # Prefer an exact verified prefix to preserve punctuation lost by clause splitting.
    if trimmed and (meaning_error or binding_error or direction_error):
        verified = verified_fallback_answer(question, matched, execution)
        if verified and verified in draft.answer:
            answer = verified
    if not answer:
        answer = verified_fallback_answer(question, matched, execution) or ""
        if not answer:
            if number_error:
                limitations.append("답변의 일부 수치를 원본 셀이나 검증된 계산에서 확인하지 못했습니다.")
            if unit_error:
                limitations.append("답변의 백분율 단위를 원본 셀이나 검증된 계산에서 확인하지 못했습니다.")
            if meaning_error:
                limitations.append("답변의 일부 의미를 인용한 원본에서 확인하지 못했습니다.")
            if binding_error:
                limitations.append("답변의 항목명과 값 연결을 원본 셀에서 확인하지 못했습니다.")
            if direction_error:
                limitations.append("답변이 말한 증감 방향이 원본 값의 변화와 달랐습니다.")
            return _blocked(
                question, execution, matched, limitations,
                "답변 내용을 원본 셀과 대조하지 못해 결과를 표시하지 않았습니다.",
            )
    if trimmed:
        limitations.append("원본에서 확인하지 못한 내용은 빼고 보여줍니다. 확인된 부분만 포함한 답변입니다.")
    verification_limited = bool(unknown or failed)
    limited = verification_limited or index_truncated or trimmed
    return QuestionAnswer(
        question=question,
        answer=answer,
        status=QuestionAnswerStatus.LIMITED if limited else QuestionAnswerStatus.ANSWERED,
        confidence=min(draft.confidence, 0.7) if verification_limited or trimmed else draft.confidence,
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
