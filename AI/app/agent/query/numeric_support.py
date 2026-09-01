from decimal import Decimal

from app.agent.execution import AgentExecution, AgentStepStatus
from app.services.insights.numeric_validation import numbers


def supported_answer_numbers(
    question: str, evidence: list[object], execution: AgentExecution
) -> set[Decimal]:
    """Return numbers that can be traced to the question or executed tools."""
    direct = _evidence_numbers(evidence)
    candidates = numbers(question) | direct
    candidates.update(_derived_numbers(direct))
    candidates.update(_comparison_numbers(execution))
    return candidates


def _evidence_numbers(evidence: list[object]) -> set[Decimal]:
    candidates = set()
    for item in evidence:
        for field in ("value", "formula", "description"):
            value = getattr(item, field, None)
            if value is not None:
                candidates.update(numbers(str(value)))
    return candidates


def _comparison_numbers(execution: AgentExecution) -> set[Decimal]:
    candidates = set()
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        comparison = step.result.data.get("time_series_comparison")
        if isinstance(comparison, dict):
            candidates.update(_trusted_values(comparison))
            candidates.update(_metric_calculations(comparison))
    return candidates


def _trusted_values(value: object, key: str | None = None) -> set[Decimal]:
    allowed = {
        "start_date",
        "end_date",
        "start_value",
        "end_value",
        "change",
    }
    if isinstance(value, dict):
        result = set()
        for child_key, child in value.items():
            result.update(_trusted_values(child, child_key))
        return result
    if isinstance(value, list):
        return {
            number
            for child in value
            for number in _trusted_values(child, key)
        }
    return numbers(str(value)) if key in allowed else set()


def _metric_calculations(comparison: dict[str, object]) -> set[Decimal]:
    candidates = set()
    metrics = comparison.get("metrics")
    if not isinstance(metrics, list):
        return candidates
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        start = _decimal(metric.get("start_value"))
        end = _decimal(metric.get("end_value"))
        if start is None or end is None:
            continue
        candidates.update(_pair_calculations(start, end))
    return candidates


def _derived_numbers(values: set[Decimal]) -> set[Decimal]:
    candidates = set()
    ordered = tuple(values)
    if ordered:
        candidates.add(abs(sum(ordered)))
        candidates.add(abs(sum(ordered) / len(ordered)))
    for start in ordered:
        for end in ordered:
            candidates.update(_pair_calculations(start, end))
    return candidates


def _pair_calculations(start: Decimal, end: Decimal) -> set[Decimal]:
    result = {abs(end - start)}
    if start:
        ratio = abs(end / start)
        result.update({ratio, ratio * 100, abs((end - start) / start * 100)})
    return result


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError):
        return None
