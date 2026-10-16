from decimal import Decimal, DecimalException

from app.agent.query.formula_resolution_functions import function
from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.agent.query.formula_resolution_operations import binary, unary
from app.agent.query.formula_resolution_reference_functions import REFERENCE_FUNCTIONS, reference_function
from app.agent.query.formula_resolution_ranges import range_argument


def evaluate_formula(node, sheet: str, resolver, inputs: set[str], depth: int = 0) -> object:
    resolver.budget.check(depth)
    evaluate = lambda child: evaluate_formula(child, sheet, resolver, inputs, depth + 1)
    if node.kind == "range":
        bound = range_argument(node, sheet, resolver)
        values = [resolver.read(reference, inputs, depth + 1) for reference in bound.references]
        return values if bound.array else values[0]
    if node.kind == "number":
        try:
            return Decimal(node.value)
        except DecimalException:
            raise FormulaUnavailable("unsupported_expression") from None
    if node.kind == "missing":
        return None
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
        if node.value in REFERENCE_FUNCTIONS:
            return reference_function(node, evaluate, sheet, resolver, inputs, depth)
        return function(node, evaluate, lambda arg: range_argument(arg, sheet, resolver).array)
    raise FormulaUnavailable("unsupported_expression")
