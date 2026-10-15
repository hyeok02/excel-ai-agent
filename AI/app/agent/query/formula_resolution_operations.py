from datetime import date, datetime, timedelta
from decimal import Decimal, DecimalException

from app.agent.query.formula_resolution_models import FormulaUnavailable
from app.agent.query.formula_resolution_values import numeric, primitive


def unary(operator: str, value: object) -> object:
    number = numeric(value)
    return {"+": lambda: number, "-": lambda: -number, "%": lambda: number / 100}[operator]()


def binary(operator: str, left: object, right: object) -> object:
    if isinstance(left, list) or isinstance(right, list):
        raise FormulaUnavailable("unsupported_expression")
    if operator in ("=", "<>", "<", ">", "<=", ">="):
        return compare(operator, left, right)
    if operator == "&":
        if any(isinstance(value, (date, datetime)) for value in (left, right)):
            raise FormulaUnavailable("unsupported_expression")
        return text_value(left) + text_value(right)
    if isinstance(left, (date, datetime)) or isinstance(right, (date, datetime)):
        return date_operation(operator, left, right)
    a, b = numeric(left), numeric(right)
    if operator == "^" and (abs(b) > 100 or b != b.to_integral_value()):
        raise FormulaUnavailable("unsupported_expression")
    try:
        value = {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
                 "/": lambda: a / b, "^": lambda: a ** int(b)}[operator]()
        return numeric(value)
    except (DecimalException, ZeroDivisionError, OverflowError):
        raise FormulaUnavailable("calculation_error") from None


def compare(operator: str, left: object, right: object) -> bool:
    if isinstance(left, bool) != isinstance(right, bool) and left is not None and right is not None:
        raise FormulaUnavailable("unsupported_expression")
    if left is None and isinstance(right, str):
        left = ""
    if right is None and isinstance(left, str):
        right = ""
    if isinstance(left, str) and isinstance(right, str):
        a, b = left.casefold(), right.casefold()
    elif isinstance(left, (date, datetime)) and isinstance(right, (date, datetime)):
        a, b = date_time(left), date_time(right)
    elif all(value is None or isinstance(value, (int, float, bool, Decimal)) for value in (left, right)):
        a, b = numeric(left), numeric(right)
    else:
        raise FormulaUnavailable("unsupported_expression")
    return {"=": lambda: a == b, "<>": lambda: a != b, "<": lambda: a < b,
            ">": lambda: a > b, "<=": lambda: a <= b, ">=": lambda: a >= b}[operator]()


def text_value(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    return str(primitive(value))


def date_operation(operator: str, left: object, right: object) -> object:
    if operator in ("+", "-") and isinstance(left, (date, datetime)) and not isinstance(right, (date, datetime)):
        offset = numeric(right)
        if offset != offset.to_integral_value() or abs(offset) > 3650000:
            raise FormulaUnavailable("unsupported_expression")
        try:
            result = left + timedelta(days=int(offset) * (1 if operator == "+" else -1))
            if min(date_time(left), date_time(result)) < datetime(1900, 3, 1):
                raise FormulaUnavailable("unsupported_expression")
            return result
        except (ValueError, OverflowError):
            raise FormulaUnavailable("calculation_error") from None
    if operator == "-" and isinstance(left, date) and isinstance(right, date):
        a, b = date_time(left), date_time(right)
        if min(a, b) < datetime(1900, 3, 1):
            raise FormulaUnavailable("unsupported_expression")
        return Decimal(str((a - b).total_seconds())) / 86400
    raise FormulaUnavailable("unsupported_expression")


def date_time(value: date) -> datetime:
    return value if isinstance(value, datetime) else datetime.combine(value, datetime.min.time())
