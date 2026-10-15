from datetime import date, datetime, timedelta
from decimal import Decimal, DecimalException, ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, localcontext

from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.agent.query.formula_resolution_values import flatten, numeric, truth

_AGGREGATES = {"SUM", "AVERAGE", "MIN", "MAX", "COUNT", "COUNTA"}
_FUNCTIONS = _AGGREGATES | {"ABS", "ROUND", "ROUNDUP", "ROUNDDOWN", "IF", "IFERROR", "AND", "OR", "NOT", "DATE", "YEAR", "MONTH", "DAY"}


def function(node, evaluate) -> object:
    name, args = node.value, node.args
    if name not in _FUNCTIONS:
        reason = "external_data" if any(marker in name for marker in ("_XLL.", "RTD", "WEBSERVICE", "OFFICE.EXCEL.FUNCTIONS")) else "unsupported_function"
        raise FormulaUnavailable(reason, (name,))
    if name == "IF":
        arity(args, 2, 3)
        return evaluate(args[1]) if truth(evaluate(args[0])) else (evaluate(args[2]) if len(args) == 3 else False)
    if name == "IFERROR":
        arity(args, 2)
        if any(may_return_array(arg) for arg in args):
            raise FormulaUnavailable("unsupported_expression")
        try:
            return evaluate(args[0])
        except FormulaUnavailable as error:
            if error.reason not in ("source_error", "calculation_error"):
                raise
            return evaluate(args[1])
    values = [evaluate(arg) for arg in args]
    if name in _AGGREGATES:
        return aggregate(name, args, values)
    if name in ("AND", "OR", "NOT"):
        arity(args, 1, 255 if name != "NOT" else 1)
        if any(value is None or isinstance(value, str) for value in flatten(values)):
            raise FormulaUnavailable("unsupported_expression")
        booleans = [truth(value) for value in flatten(values)]
        return all(booleans) if name == "AND" else any(booleans) if name == "OR" else not booleans[0]
    if name in ("DATE", "YEAR", "MONTH", "DAY"):
        return date_function(name, values)
    arity(args, 1 if name == "ABS" else 2)
    if name == "ABS":
        return abs(numeric(values[0]))
    number, digits = numeric(values[0]), numeric(values[1])
    if digits != digits.to_integral_value() or abs(digits) > 100:
        raise FormulaUnavailable("unsupported_expression")
    try:
        precision = max(28, len(number.as_tuple().digits), number.adjusted() + int(digits) + 1) + 4
        if precision > 8192:
            raise FormulaUnavailable("resource_limit")
        with localcontext() as context:
            context.prec = precision
            return number.quantize(Decimal(1).scaleb(-int(digits)), rounding={
                "ROUND": ROUND_HALF_UP, "ROUNDUP": ROUND_UP, "ROUNDDOWN": ROUND_DOWN,
            }[name])
    except DecimalException:
        raise FormulaUnavailable("unsupported_expression") from None


def arity(args, minimum: int, maximum: int | None = None) -> None:
    if not minimum <= len(args) <= (maximum if maximum is not None else minimum):
        raise FormulaUnavailable("unsupported_expression")


def aggregate(name: str, args, values: list) -> object:
    arity(args, 1, 255)
    if name == "COUNTA":
        return sum(value is not None for value in flatten(values))
    numbers = []
    for arg, value in zip(args, values):
        referenced = arg.kind == "range" or isinstance(value, list)
        for item in value if isinstance(value, list) else [value]:
            if item is None:
                continue
            if referenced and isinstance(item, (bool, str)):
                continue
            if not referenced and isinstance(item, str):
                try:
                    item = Decimal(item)
                except DecimalException:
                    if name == "COUNT":
                        continue
                    raise FormulaUnavailable("calculation_error") from None
            numbers.append(numeric(item))
    if name == "COUNT":
        return len(numbers)
    if name == "SUM":
        return sum(numbers, Decimal(0))
    if name in ("MIN", "MAX"):
        return (min if name == "MIN" else max)(numbers) if numbers else Decimal(0)
    if not numbers:
        raise FormulaUnavailable("calculation_error")
    return sum(numbers) / len(numbers)


def date_function(name: str, values: list) -> object:
    arity(values, 3 if name == "DATE" else 1)
    if name != "DATE":
        value = values[0]
        if not isinstance(value, (date, datetime)):
            raise FormulaUnavailable("unsupported_expression")
        return getattr(value, name.lower())
    numbers = [numeric(value) for value in values]
    if any(value != value.to_integral_value() for value in numbers):
        raise FormulaUnavailable("unsupported_expression")
    year, month, day = map(int, numbers)
    year = year + 1900 if 0 <= year < 1900 else year
    if not 1 <= year <= 9999 or abs(month) > 120 or abs(day) > 3660:
        raise FormulaUnavailable("unsupported_expression")
    year += (month - 1) // 12
    month = (month - 1) % 12 + 1
    if year == 1900 and month <= 3:
        raise FormulaUnavailable("unsupported_expression")  # Excel's fictitious leap day.
    try:
        result = date(year, month, 1) + timedelta(days=day - 1)
        if result < date(1900, 3, 1):
            raise FormulaUnavailable("unsupported_expression")
        return result
    except (ValueError, OverflowError):
        raise FormulaUnavailable("calculation_error") from None


def may_return_array(node) -> bool:
    if node.kind == "range":
        return ":" in node.value.rsplit("!", 1)[-1]
    if node.kind == "function" and node.value in _AGGREGATES | {"AND", "OR"}:
        return False
    return any(may_return_array(arg) for arg in node.args)
