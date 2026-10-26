"""Answer a relevant question directly from an already verified insight."""

from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.comparison_evidence import (
    available_evidence,
    matched_comparison_evidence,
    present_comparison_evidence,
)
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.verified_insight_constraints import insight_intent_matches
from app.agent.query.verified_insight_selection import requested_insight_items
from app.agent.query.verified_insight_matching import (
    MIN_RELEVANCE_SCORE,
    verified_insight_score,
)

MAX_PRESENTED_EVIDENCE = 120


def validated_verified_insight_answer(
    question: str,
    execution: AgentExecution,
    index_truncated: bool,
    intent: QuestionIntent | None = None,
) -> QuestionAnswer | None:
    """Reuse one clearly matching fact; ambiguous matches still fall through."""
    available = available_evidence(execution)
    if not available:
        return None
    asked = intent.enriched(question) if intent is not None else question
    answer_kind = intent.kind if intent is not None else ""
    ranked = []
    for order, item in enumerate(requested_insight_items(question, _verified_items(execution))):
        fact = str(item.get("fact") or "").strip()
        if not fact or not insight_intent_matches(question, item, answer_kind):
            continue
        score = verified_insight_score(question, asked, item)
        if score < MIN_RELEVANCE_SCORE:
            continue
        references = _support_references(item)
        evidence, missing = matched_comparison_evidence(references, available)
        if not evidence or missing:
            continue
        ranked.append((score, -order, fact, evidence, item))
    if not ranked:
        return None
    ranked.sort(key=lambda candidate: (candidate[0], candidate[1]), reverse=True)
    if len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        return None
    _, _, fact, evidence, item = ranked[0]
    failed = any(step.status is AgentStepStatus.FAILED for step in execution.steps)
    limitations = []
    if index_truncated:
        limitations.append("대용량 워크북의 일부 관련 셀은 검색 범위에서 제외되었습니다.")
    if failed:
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    limited = bool(limitations)
    confidence = _confidence(item, 0.7 if limited else 1.0)
    return QuestionAnswer(
        question=question,
        answer=fact,
        status=QuestionAnswerStatus.LIMITED if limited else QuestionAnswerStatus.ANSWERED,
        confidence=confidence,
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[
            present_comparison_evidence(value)
            for value in evidence[:MAX_PRESENTED_EVIDENCE]
        ],
        limitations=limitations,
        # Reuse checks citations and the canonical fact, not the full request scope.
        verification=QuestionAnswerVerification(
            level="source_checked", checks=["cited_cells", "verified_insight_fact"]
        ),
    )


def _verified_items(execution: AgentExecution):
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        values = step.result.data.get("verified_insights")
        if isinstance(values, list):
            yield from (value for value in values if isinstance(value, dict))


def _support_references(item: dict[str, object]) -> list[str]:
    values = item.get("support_references")
    if not isinstance(values, list):
        values = item.get("required_references")
    if not isinstance(values, list):
        return []
    return list(dict.fromkeys(value for value in values if isinstance(value, str)))


def _confidence(item: dict[str, object], ceiling: float) -> float:
    try:
        return max(0.0, min(float(item.get("confidence", ceiling)), ceiling))
    except (TypeError, ValueError):
        return ceiling
