"""Verify numeric results emitted by successful Agent Tool executions."""
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from statistics import median

from app.agent.execution import AgentExecution, AgentStepStatus

OPERATIONS = {
    "difference", "percent_change", "sum", "average",
    "median", "min", "max", "count",
}


@dataclass(frozen=True)
class VerifiedCalculation:
    operation: str
    result: Decimal
    unit: str


def verified_calculations(
    evidence: list[object], execution: AgentExecution
) -> list[VerifiedCalculation]:
    cited = _cited_values(evidence)
    verified = []
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        raw_items = step.result.data.get("calculations")
        if not isinstance(raw_items, list):
            continue
        for raw in raw_items:
            item = _verify(raw, cited)
            if item:
                verified.append(item)
    return verified


def _verify(raw: object, cited: dict[str, object]) -> VerifiedCalculation | None:
    if not isinstance(raw, dict):
        return None
    operation = raw.get("operation")
    references = raw.get("operand_references")
    raw_values = raw.get("operand_values")
    unit = raw.get("unit")
    result = _decimal(raw.get("result"))
    if (
        operation not in OPERATIONS
        or not isinstance(references, list)
        or not isinstance(raw_values, list)
        or not isinstance(unit, str)
        or not unit.strip()
        or result is None
        or len(references) != len(raw_values)
        or not references
    ):
        return None
    normalized = [_normalize_reference(reference) for reference in references]
    if any(
        not reference or reference not in cited
        for reference in normalized
    ):
        return None
    if operation == "count":
        if any(cited[reference] != value for reference, value in zip(normalized, raw_values)):
            return None
        operands = [Decimal(1)] * len(raw_values)
    else:
        values = [_decimal(value) for value in raw_values]
        if any(value is None for value in values):
            return None
        operands = [value for value in values if value is not None]
        if any(
            _decimal(cited[reference]) != value
            for reference, value in zip(normalized, operands)
        ):
            return None
    expected = _calculate(str(operation), operands)
    if expected is None or not _same_number(expected, result):
        return None
    return VerifiedCalculation(str(operation), result, unit.strip())


def _calculate(operation: str, values: list[Decimal]) -> Decimal | None:
    if operation in {"difference", "percent_change"} and len(values) != 2:
        return None
    if operation == "difference":
        return values[1] - values[0]
    if operation == "percent_change":
        return ((values[1] - values[0]) / abs(values[0]) * 100) if values[0] else None
    if operation == "sum":
        return sum(values)
    if operation == "average":
        return sum(values) / len(values)
    if operation == "median":
        return Decimal(str(median(values)))
    if operation == "min":
        return min(values)
    if operation == "max":
        return max(values)
    if operation == "count":
        return Decimal(len(values))
    return None


def _cited_values(evidence: list[object]) -> dict[str, object]:
    result = {}
    for item in evidence:
        sheet = getattr(item, "sheet_name", None)
        reference = getattr(item, "reference", None)
        value = getattr(item, "value", None)
        if isinstance(sheet, str) and isinstance(reference, str) and value is not None:
            result[_normalize_reference(f"{sheet}!{reference}")] = value
    return result


def _normalize_reference(value: object) -> str:
    return str(value).strip().replace("'", "").replace("$", "").casefold()


def _decimal(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = Decimal(str(value).replace(",", ""))
        return parsed if parsed.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def _same_number(expected: Decimal, actual: Decimal) -> bool:
    tolerance = max(Decimal("1e-9"), abs(expected) * Decimal("1e-9"))
    return abs(expected - actual) <= tolerance
