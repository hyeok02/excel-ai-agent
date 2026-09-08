from dataclasses import dataclass
from datetime import date

from app.agent.execution import AgentExecution
from app.agent.query.models import QuestionAnswerEvidence
from app.agent.query.references import matching_references, normalize_reference


@dataclass(frozen=True)
class VerifiedComparisonAnswer:
    text: str
    references: tuple[str, ...]
    value_checks: tuple[tuple[str, object], ...]
    header: str
    header_references: tuple[str, ...]


def available_evidence(execution: AgentExecution) -> dict[str, object]:
    available = {}
    for step in execution.steps:
        if not step.result:
            continue
        for item in step.result.evidence:
            if not item.reference:
                continue
            key = normalize_reference(f"{item.sheet_name}!{item.reference}")
            current = available.get(key)
            if key and (current is None or _quality(item) > _quality(current)):
                available[key] = item
    return available


def comparison_values_match(
    checks: tuple[tuple[str, object], ...], available: dict[str, object]
) -> bool:
    keys = set(available)
    for reference, expected in checks:
        normalized = normalize_reference(reference)
        resolved = matching_references(normalized, keys) if normalized else set()
        if not any(
            _same_value(getattr(available[key], "value", None), expected)
            for key in resolved
        ):
            return False
    return True


def matched_comparison_evidence(references, available):
    matched, missing, seen = [], [], set()
    keys = set(available)
    for reference in references:
        normalized = normalize_reference(reference)
        resolved = matching_references(normalized, keys) if normalized else set()
        if not resolved:
            missing.append(reference)
        for key in available:
            if key in resolved and key not in seen:
                matched.append(available[key])
                seen.add(key)
    return matched, missing


def present_comparison_evidence(item) -> QuestionAnswerEvidence:
    content = item.formula or (str(item.value) if item.value is not None else "")
    label = f"{item.description}: {content}" if content else item.description
    return QuestionAnswerEvidence(**item.model_dump(), label=label[:160])


def comparison_number(value: object, unit: str) -> str:
    number = float(value)
    rendered = (
        f"{int(number):,}"
        if number.is_integer()
        else f"{number:,.2f}".rstrip("0").rstrip(".")
    )
    return f"{rendered}{unit}"


def comparison_period(value: object) -> str:
    try:
        parsed = date.fromisoformat(str(value))
        return f"{parsed.year}년 {parsed.month}월 {parsed.day}일"
    except ValueError:
        return str(value or "해당 기간")


def comparison_change_matches(start: object, end: object, change: object) -> bool:
    try:
        return abs(float(end) - float(start) - float(change)) < 1e-9
    except (TypeError, ValueError):
        return False


def comparison_header_matches(
    header: str, references: tuple[str, ...], available: dict[str, object]
) -> bool:
    keys = set(available)
    for reference in references:
        normalized = normalize_reference(reference)
        resolved = matching_references(normalized, keys) if normalized else set()
        if any(
            str(getattr(available[key], "value", "")).casefold() == header.casefold()
            for key in resolved
        ):
            return True
    return False


def _same_value(actual: object, expected: object) -> bool:
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return abs(float(actual) - float(expected)) < 1e-9
    return actual == expected


def _quality(item: object) -> int:
    return 2 * int(getattr(item, "value", None) is not None) + int(
        bool(getattr(item, "formula", None))
    )
