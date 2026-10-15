import re
from decimal import Decimal, InvalidOperation

from app.agent.execution import AgentExecution
from app.agent.query.calculations import verified_calculations
from app.agent.query.derived_numbers import derived_numbers, derived_percent_numbers
from app.services.insights.display.percent_format import scales_by_percent
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
    question: str,
    evidence: list[object],
    execution: AgentExecution,
    answer: str = "",
) -> set[Decimal]:
    """Return numbers that can be traced to the question or executed tools."""
    candidates = numbers(question) | _evidence_numbers(evidence)
    candidates.update(
        abs(item.result) for item in verified_calculations(evidence, execution)
    )
    candidates.update(derived_numbers(answer, evidence))
    candidates.update(derived_percent_numbers(answer, evidence))
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
    candidates.update(derived_percent_numbers(answer, evidence))
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
        number_format = getattr(item, "number_format", None)
        if number_format:
            context += f" {number_format}"
        if isinstance(value, str):
            context = f"{context} {value}"
        header = _cited_column_header(item, evidence)
        if header:
            context += f" {header}"
        if value is not None and PERCENT_CONTEXT.search(context):
            candidates.update(_display_percent_values(value, number_format))
    return candidates


def _display_percent_values(value: object, number_format: str | None = None) -> set[Decimal]:
    if isinstance(value, str) and PERCENT_MARKER.search(value):
        return {number for number, _ in _percent_claims(value)}
    number = _decimal(value)
    if number is None:
        return set()
    number = abs(number)
    # Excel's percent format has a fixed x100 display scale, even for values
    # above one. A (%) column with a General/numeric format stores percentage
    # points; magnitude alone cannot tell 0.4% from 40%.
    if number_format is not None:
        return {number * 100 if scales_by_percent(number_format) else number}
    return {number * 100 if number <= 1 else number}


def _cited_column_header(item: object, evidence: list[object]) -> str:
    """Only a cited, preceding text cell in this column can supply its unit.

    A percentage in another column or another worksheet must not turn a raw
    amount into a percentage. The nearest cited text cell is used so a more
    distant header cannot leak through an intervening text record.
    """
    address = re.fullmatch(r"([A-Z]+)(\d+)", str(getattr(item, "reference", "")).replace("$", ""), re.I)
    if not address:
        return ""
    sheet = getattr(item, "sheet_name", None)
    column, row = address.group(1).upper(), int(address.group(2))
    candidates = []
    for other in evidence:
        value = getattr(other, "value", None)
        if getattr(other, "sheet_name", None) != sheet or not isinstance(value, str):
            continue
        reference = re.fullmatch(r"([A-Z]+)(\d+)", str(getattr(other, "reference", "")).replace("$", ""), re.I)
        if reference and reference.group(1).upper() == column and int(reference.group(2)) < row:
            candidates.append((int(reference.group(2)), value))
    return max(candidates, default=(0, ""))[1]


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
