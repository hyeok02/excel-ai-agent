from app.agent.query.formula_resolution_conditions import CONDITIONAL_FUNCTIONS, conditional_function
from app.agent.query.formula_resolution_functions import may_return_array
from app.agent.query.formula_resolution_lookups import LOOKUP_FUNCTIONS, lookup_function
from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.agent.query.formula_resolution_ranges import range_argument

REFERENCE_FUNCTIONS = CONDITIONAL_FUNCTIONS | LOOKUP_FUNCTIONS | {"_XLFN.XLOOKUP"}


def reference_function(node, evaluate, sheet, resolver, inputs, depth):
    array = lambda arg: may_return_array(arg, lambda item: range_argument(item, sheet, resolver).array)
    def scalar(arg):
        # Reject arrays before their evaluation can turn one element's error into
        # an apparently valid scalar IFERROR fallback.
        if array(arg):
            raise FormulaUnavailable("unsupported_expression")
        value = evaluate(arg)
        if isinstance(value, list):
            raise FormulaUnavailable("unsupported_expression")
        return value

    name = node.value.removeprefix("_XLFN.")
    if name in CONDITIONAL_FUNCTIONS:
        start = (1 if name.startswith("COUNT") else 2) if name.endswith("IFS") else 1
        scalar_positions = range(start, len(node.args), 2) if name.endswith("IFS") else (1,)
    else:
        scalar_positions = {"INDEX": (1, 2), "MATCH": (0, 2), "VLOOKUP": (0, 2, 3),
                            "HLOOKUP": (0, 2, 3), "XLOOKUP": (0, 3, 4, 5)}[name]
    if any(array(node.args[i]) for i in scalar_positions if i < len(node.args)):
        raise FormulaUnavailable("unsupported_expression")
    reference = lambda arg: range_argument(arg, sheet, resolver)
    read = lambda address: resolver.read(address, inputs, depth + 1)
    handler = conditional_function if node.value in CONDITIONAL_FUNCTIONS else lookup_function
    return handler(node, scalar, reference, read)
