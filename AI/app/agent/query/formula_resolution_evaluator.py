from decimal import Decimal, DecimalException

from app.agent.query.formula_resolution_functions import function
from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.agent.query.formula_resolution_operations import binary, unary
from app.agent.query.formula_resolution_references import reference_cells


def evaluate_formula(node, sheet: str, resolver, inputs: set[str], depth: int = 0) -> object:
    resolver.budget.check(depth)
    evaluate = lambda child: evaluate_formula(child, sheet, resolver, inputs, depth + 1)
    if node.kind == "range":
        refs = reference_cells(node.value, sheet, resolver.sheets, resolver.limits.max_range_cells)
        values = [resolver.read(reference, inputs, depth + 1) for reference in refs]
        return values if ":" in node.value.rsplit("!", 1)[-1] else values[0]
    if node.kind == "number":
        try:
            return Decimal(node.value)
        except DecimalException:
            raise FormulaUnavailable("unsupported_expression") from None
    if node.kind == "logical":
        return node.value.upper() == "TRUE"
    if node.kind == "text":
        return node.value[1:-1].replace('""', '"')
    if node.kind == "error":
        raise FormulaUnavailable("source_error", (node.value,))
    if node.kind == "unary":
        return unary(node.value, evaluate(node.args[0]))
    if node.kind == "binary":
        return resolver.bounded_value(binary(node.value, evaluate(node.args[0]), evaluate(node.args[1])))
    if node.kind == "function":
        return function(node, evaluate)
    raise FormulaUnavailable("unsupported_expression")
