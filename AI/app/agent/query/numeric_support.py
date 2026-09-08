import re
from decimal import Decimal, InvalidOperation

from app.agent.execution import AgentExecution
from app.agent.query.calculations import verified_calculations
from app.services.insights.verification.numeric_validation import (
    NUMBER_PATTERN,
    numbers,
)

PERCENT = r"(?:[%％]|퍼센트|(?<![A-Za-z])percent(?:age)?(?![A-Za-z]))"
PERCENT_MARKER = re.compile(PERCENT, re.I)
PERCENT_VALUE = re.compile(rf"({NUMBER_PATTERN.pattern})\s*{PERCENT}", re.I)
PERCENT_CONTEXT = re.compile(
    r"[%％]|(?<![A-Za-z])(?:percent(?:age)?|rate|ratio)(?![A-Za-z])|"
    r"비율|증감률|성장률|마진",
    re.I,
)


def supported_answer_numbers(
    question: str, evidence: list[object], execution: AgentExecution
) -> set[Decimal]:
    """Return numbers that can be traced to the question or executed tools."""
    candidates = numbers(question) | _evidence_numbers(evidence)
    candidates.update(
        abs(item.result) for item in verified_calculations(evidence, execution)
    )
    return candidates


def _evidence_numbers(evidence: list[object]) -> set[Decimal]:
    candidates = set()
    for item in evidence:
        value = getattr(item, "value", None)
        if value is not None:
            candidates.update(numbers(str(value)))
    return candidates


def answer_units_supported(
    answer: str, evidence: list[object], execution: AgentExecution
) -> bool:
    """Require percentage claims to have percentage-typed source provenance."""
    if not PERCENT_MARKER.search(answer):
        return True
    candidates = _direct_percent_numbers(evidence)
    candidates.update(
        abs(item.result)
        for item in verified_calculations(evidence, execution)
        if item.unit.casefold() == "percent"
    )
    claims = _percent_claims(answer)
    if not claims:
        return bool(candidates)
    return all(
        any(abs(candidate - value) <= tolerance for candidate in candidates)
        for value, tolerance in claims
    )


def _direct_percent_numbers(evidence: list[object]) -> set[Decimal]:
    candidates = set()
    for item in evidence:
        context = " ".join(
            str(getattr(item, field, "") or "")
            for field in ("value_type", "description", "header", "label")
        )
        value = getattr(item, "value", None)
        if isinstance(value, str):
            context = f"{context} {value}"
        if value is not None and PERCENT_CONTEXT.search(context):
            candidates.update(_display_percent_values(value))
    return candidates


def _display_percent_values(value: object) -> set[Decimal]:
    if isinstance(value, str) and PERCENT_MARKER.search(value):
        return {number for number, _ in _percent_claims(value)}
    number = _decimal(value)
    if number is None:
        return set()
    number = abs(number)
    return {number * 100 if number <= 1 else number}


def _percent_claims(value: str) -> list[tuple[Decimal, Decimal]]:
    claims = []
    for match in PERCENT_VALUE.finditer(value):
        number = _decimal(match.group(1))
        if number is None:
            continue
        number = abs(number)
        tolerance = Decimal("0.5") * (Decimal(10) ** number.as_tuple().exponent)
        claims.append((number, tolerance))
    return claims


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value).replace(",", "").strip())
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, ValueError):
        return None
