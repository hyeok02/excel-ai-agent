from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.comparison_evidence import (
    VerifiedComparisonAnswer,
    available_evidence,
    comparison_change_matches,
    comparison_header_matches,
    comparison_number,
    comparison_period,
    comparison_values_match,
    matched_comparison_evidence,
    present_comparison_evidence,
)
from app.agent.query.models import (
    QuestionAnswer,
    QuestionAnswerStatus,
)
from app.services.insights.display.glossary import readable


EXTREME_WORDS = ("가장", "제일", "최대", "most", "largest", "biggest")
GROUP_NAMES = {"department": "부서", "role": "직무"}


def validated_comparison_answer(
    question: str,
    execution: AgentExecution,
    index_truncated: bool,
    available: dict[str, object] | None = None,
) -> QuestionAnswer | None:
    available = available if available is not None else available_evidence(execution)
    canonical = verified_comparison_answer(question, execution)
    if canonical is None:
        return None
    evidence, missing = matched_comparison_evidence(canonical.references, available)
    if (
        not evidence or missing
        or not comparison_values_match(canonical.value_checks, available)
        or not comparison_header_matches(
            canonical.header, canonical.header_references, available
        )
    ):
        return None
    failed = any(step.status is AgentStepStatus.FAILED for step in execution.steps)
    limitations = []
    if index_truncated:
        limitations.append("대용량 워크북의 일부 관련 셀은 검색 범위에서 제외되었습니다.")
    if failed:
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    limited = bool(limitations)
    return QuestionAnswer(
        question=question,
        answer=canonical.text,
        status=QuestionAnswerStatus.LIMITED if limited else QuestionAnswerStatus.ANSWERED,
        confidence=0.7 if limited else 1.0,
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[present_comparison_evidence(item) for item in evidence],
        limitations=limitations,
    )


def verified_comparison_answer(
    question: str, execution: AgentExecution
) -> VerifiedComparisonAnswer | None:
    if not any(word in question.casefold() for word in EXTREME_WORDS):
        return None
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        comparison = step.result.data.get("time_series_comparison")
        answer = _answer(question, comparison)
        if answer:
            return answer
    return None


def _answer(question: str, comparison: object) -> VerifiedComparisonAnswer | None:
    if not isinstance(comparison, dict):
        return None
    direction = comparison.get("change_direction")
    group = comparison.get("metric_group")
    ranked = comparison.get("ranked_changes")
    if direction not in {"decrease", "increase"} or group not in GROUP_NAMES:
        return None
    if not isinstance(ranked, list) or not ranked or not isinstance(ranked[0], dict):
        return None
    metric = ranked[0]
    required = ("header", "start_value", "end_value", "change")
    if any(metric.get(key) is None for key in required):
        return None
    header = metric["header"]
    header_references = metric.get("header_references")
    if not isinstance(header, str) or not isinstance(header_references, list):
        return None
    header_references = tuple(item for item in header_references if isinstance(item, str))
    if not header_references:
        return None
    start_reference = metric.get("start_reference")
    end_reference = metric.get("end_reference")
    if not isinstance(start_reference, str) or not isinstance(end_reference, str):
        return None
    if not comparison_change_matches(
        metric["start_value"], metric["end_value"], metric["change"]
    ):
        return None
    references = _references(comparison, metric)
    if len(references) < 4:
        return None
    unit = "명" if "명" in question or group in {"department", "role"} else ""
    start = comparison_number(metric["start_value"], unit)
    end = comparison_number(metric["end_value"], unit)
    change = comparison_number(abs(float(metric["change"])), unit)
    verb = "감소" if direction == "decrease" else "증가"
    subject = readable(header)
    text = (
        f"{comparison_period(comparison.get('start_date'))}부터 "
        f"{comparison_period(comparison.get('end_date'))}까지 가장 많이 {verb}한 "
        f"{GROUP_NAMES[group]}는 {subject}입니다. "
        f"{start}에서 {end}으로 {change} {verb}했습니다."
    )
    checks = (
        (start_reference, metric["start_value"]),
        (end_reference, metric["end_value"]),
    )
    return VerifiedComparisonAnswer(
        text, tuple(references), checks, header, header_references
    )


def _references(comparison: dict, metric: dict) -> list[str]:
    header_references = metric.get("header_references")
    values = [
        *(header_references if isinstance(header_references, list) else []),
        comparison.get("start_reference"),
        comparison.get("end_reference"),
        metric.get("start_reference"),
        metric.get("end_reference"),
    ]
    return list(dict.fromkeys(value for value in values if isinstance(value, str)))
