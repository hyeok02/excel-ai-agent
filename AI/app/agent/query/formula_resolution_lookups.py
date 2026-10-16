"""Exact workbook-only lookups; approximate, binary and spilling modes stay closed."""
from app.agent.query.formula_resolution_functions import arity
from app.agent.query.formula_resolution_matching import exact_match
from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.agent.query.formula_resolution_ranges import integer_argument, optional_integer

LOOKUP_FUNCTIONS = {"INDEX", "MATCH", "VLOOKUP", "HLOOKUP", "XLOOKUP"}


def lookup_function(node, evaluate, reference, read):
    name, args = node.value.removeprefix("_XLFN."), node.args
    if name == "INDEX":
        arity(args, 2, 3)
        source = reference(args[0])
        if args[1].kind == "missing" and (len(args) == 2 or source.rows != 1):
            raise FormulaUnavailable("unsupported_expression")
        if len(args) == 3 and args[2].kind == "missing" and source.columns != 1:
            raise FormulaUnavailable("unsupported_expression")
        row = optional_integer(args, 1, 1, evaluate)
        column = optional_integer(args, 2, 1, evaluate)
        if len(args) == 2:
            source.vector()  # Omitting an axis in a matrix yields an unsupported array.
            if source.rows == 1:
                row, column = 1, row
        if not row or not column:
            raise FormulaUnavailable("unsupported_expression")
        if not 1 <= row <= source.rows or not 1 <= column <= source.columns:
            raise FormulaUnavailable("source_error", ("#REF!",))
        return read(source.references[(row - 1) * source.columns + column - 1])
    if name == "MATCH":
        arity(args, 3)
        if integer_argument(evaluate(args[2])) != 0:
            raise FormulaUnavailable("unsupported_expression")
        position = find(evaluate(args[0]), reference(args[1]).vector(), read, wildcards=True)
        if position is None:
            raise FormulaUnavailable("source_error", ("#N/A",))
        return position + 1
    if name in ("VLOOKUP", "HLOOKUP"):
        arity(args, 4)
        if integer_argument(evaluate(args[3])) != 0:
            raise FormulaUnavailable("unsupported_expression")
        source, selected = reference(args[1]), integer_argument(evaluate(args[2]))
        maximum = source.columns if name == "VLOOKUP" else source.rows
        if selected < 1 or selected > maximum:
            raise FormulaUnavailable("source_error", ("#REF!",))
        keys = source.references[::source.columns] if name == "VLOOKUP" else source.references[:source.columns]
        position = find(evaluate(args[0]), keys, read, wildcards=True)
        if position is None:
            raise FormulaUnavailable("source_error", ("#N/A",))
        offset = position * source.columns + selected - 1 if name == "VLOOKUP" else (selected - 1) * source.columns + position
        return lookup_value(read(source.references[offset]))
    arity(args, 3, 6)
    mode, direction = optional_integer(args, 4, 0, evaluate), optional_integer(args, 5, 1, evaluate)
    if mode not in (0, 2) or direction not in (1, -1):
        raise FormulaUnavailable("unsupported_expression")
    keys, results = reference(args[1]), reference(args[2])
    if keys.shape != results.shape:
        raise FormulaUnavailable("unsupported_expression")
    keys.vector()
    position = find(evaluate(args[0]), keys.references, read, wildcards=mode == 2, reverse=direction == -1)
    if position is not None:
        return lookup_value(read(results.references[position]))
    if len(args) > 3 and args[3].kind != "missing":
        value = evaluate(args[3])
        if isinstance(value, list):
            raise FormulaUnavailable("unsupported_expression")
        return value
    raise FormulaUnavailable("source_error", ("#N/A",))


def lookup_value(value):
    if value is None:
        # A blank returned by a lookup has context-dependent value/reference
        # coercion (e.g. COUNTA versus concatenation). Do not guess a scalar.
        raise FormulaUnavailable("unsupported_expression")
    return value


def find(key, references, read, wildcards=False, reverse=False):
    positions = range(len(references) - 1, -1, -1) if reverse else range(len(references))
    for position in positions:
        try:
            value = read(references[position])
        except FormulaUnavailable as error:
            if error.reason in {"source_error", "calculation_error"}:
                raise FormulaUnavailable("unsupported_expression", (references[position],)) from None
            raise
        if exact_match(key, value, wildcards):
            return position
    return None
