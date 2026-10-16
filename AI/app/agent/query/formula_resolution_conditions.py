"""Conditional aggregates with aligned ranges and recorded source dependencies."""
from decimal import Decimal

from app.agent.query.formula_resolution_functions import arity
from app.agent.query.formula_resolution_matching import criterion_match
from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.agent.query.formula_resolution_values import numeric

CONDITIONAL_FUNCTIONS = {"SUMIF", "SUMIFS", "COUNTIF", "COUNTIFS", "AVERAGEIF", "AVERAGEIFS"}


def conditional_function(node, evaluate, reference, read):
    name, args = node.value, node.args
    counted = name.startswith("COUNT")
    multiple = name.endswith("IFS")
    if multiple:
        arity(args, 2 if counted else 3, 254 if counted else 255)
        start = 0 if counted else 1
        if (len(args) - start) % 2:
            raise FormulaUnavailable("unsupported_expression")
        pairs = [(reference(args[i]), evaluate(args[i + 1])) for i in range(start, len(args), 2)]
        summed = None if counted else reference(args[0])
    else:
        arity(args, 2, 2 if counted else 3)
        pairs = [(reference(args[0]), evaluate(args[1]))]
        summed = None if counted else reference(args[2] if len(args) == 3 else args[0])
    shape = pairs[0][0].shape
    if any(item.shape != shape for item, _ in pairs) or (summed and summed.shape != shape):
        # SUMIF may resize its sum range in Excel; we never silently zip unlike shapes.
        raise FormulaUnavailable("unsupported_expression")
    total, count = Decimal(0), 0
    for position in range(len(pairs[0][0].references)):
        # Evaluate every condition even if another excludes the row: unknown inputs
        # must not silently become a non-match and produce a seemingly exact total.
        matches = [criterion_match(criterion, criterion_value(item.references[position], read)) for item, criterion in pairs]
        if not all(matches):
            continue
        if counted:
            count += 1
            continue
        value = read(summed.references[position])
        if value is None or isinstance(value, str):
            continue
        if isinstance(value, bool):
            raise FormulaUnavailable("unsupported_expression")
        total += numeric(value)
        count += 1
    if counted:
        return count
    if name.startswith("AVERAGE"):
        if not count:
            raise FormulaUnavailable("calculation_error")
        return total / count
    return total


def criterion_value(reference, read):
    try:
        return read(reference)
    except FormulaUnavailable as error:
        if error.reason in {"source_error", "calculation_error"}:
            # Conditional functions have special error-cell matching semantics;
            # an unsupported case is not an Excel error for IFERROR to replace.
            raise FormulaUnavailable("unsupported_expression", (reference,)) from None
        raise
