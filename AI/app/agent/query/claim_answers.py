"""Structured claims are checked individually, without trusting generated prose."""
from types import SimpleNamespace

from app.agent.execution import AgentStepStatus
from app.agent.query.comparison_evidence import available_evidence, present_comparison_evidence
from app.agent.query.models import (QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification,
                                    QuestionVerificationLevel)
from app.agent.query.source_claims import render_claim

UNKNOWN = "인용한 원본에서 확인한 값·배치 외의 의미, 원인이나 관계는 확인하지 못했습니다."
REJECTED = "원본 주소·대상·항목·기간 연결을 확인하지 못한 주장은 제외했습니다."


def validated_claim_answer(question, draft, execution, index_truncated, available):
    if not draft.claims:
        return None
    available = available_evidence(SimpleNamespace(steps=[
        step for step in execution.steps if step.status is AgentStepStatus.SUCCEEDED
    ]))
    sentences, evidence, limitations = [], {}, []
    cell_interpretation_unchecked = False
    for claim in draft.claims:
        if claim.kind == "unknown":
            limitations.append(UNKNOWN)
        elif result := render_claim(claim, question, available, execution):
            sentence, sources = result.sentence, result.evidence
            sentences.append(sentence)
            evidence.update({(item.sheet_name, item.reference): item for item in sources})
            if claim.kind == "cell_value" and not result.complete_lookup:
                cell_interpretation_unchecked = True
        else:
            limitations.append(REJECTED)
    if index_truncated:
        limitations.append("대용량 워크북의 일부 셀은 검색 범위에서 제외되었습니다.")
    if any(step.status is AgentStepStatus.FAILED for step in execution.steps):
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    # Model-authored limitations may contain new unsupported claims too. Use only
    # canonical scope disclosures; never append an arbitrary assertion as a caveat.
    if draft.limitations:
        limitations.append(UNKNOWN)
    if cell_interpretation_unchecked and sentences:
        limitations.append("원본 셀의 값과 배치를 확인한 답변이며 표시의 업무상 의미는 해석하지 않았습니다.")
    if not sentences:
        return QuestionAnswer(
            question=question, answer="현재 원본 근거로 확인 가능한 답변이 없습니다.",
            status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE, confidence=0,
            selected_tools=[step.tool_name for step in execution.steps], evidence=[],
            limitations=list(dict.fromkeys(limitations or [UNKNOWN])),
        )
    return QuestionAnswer(
        question=question, answer="\n\n".join(dict.fromkeys(sentences)),
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        confidence=min(draft.confidence, 0.7) if limitations else draft.confidence,
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[present_comparison_evidence(item) for item in evidence.values()],
        limitations=list(dict.fromkeys(limitations)),
        verification=QuestionAnswerVerification(
            level=QuestionVerificationLevel.SOURCE_CHECKED,
            checks=["cited_cells", "source_values", "claim_bindings", "claim_semantics"],
        ),
    )
