from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from math import isfinite

from app.agent.query.formula_resolution_models import FormulaUnavailable

EXCEL_ERRORS = {"#NULL!", "#DIV/0!", "#VALUE!", "#REF!", "#NAME?", "#NUM!", "#N/A", "#SPILL!", "#CALC!"}


def numeric(value: object) -> Decimal:
    if value is None:
        return Decimal(0)
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, (int, float, Decimal, str)):
        try:
            result = Decimal(str(value))
        except InvalidOperation:
            raise FormulaUnavailable("calculation_error") from None
        if not result.is_finite():
            raise FormulaUnavailable("calculation_error")
        if result.copy_abs() > Decimal("1e308"):
            raise FormulaUnavailable("unsupported_expression")
        return result
    raise FormulaUnavailable("unsupported_expression")


def primitive(value: object) -> str | int | float | bool | None:
    if isinstance(value, Decimal):
        numeric(value)
        result = float(value)
        if not isfinite(result):
            raise FormulaUnavailable("calculation_error")
        return int(value) if value == value.to_integral_value() and abs(value) < 1e15 else result
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not isfinite(value):
            raise FormulaUnavailable("calculation_error")
        return value
    raise FormulaUnavailable("unsupported_expression")


def truth(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, (Decimal, int, float, bool)):
        return bool(numeric(value))
    raise FormulaUnavailable("unsupported_expression")


def flatten(values: list) -> list:
    return [item for value in values for item in (value if isinstance(value, list) else [value])]


def source_value(cell) -> object:
    value = cell.value
    if isinstance(value, str) and value.upper() in EXCEL_ERRORS:
        raise FormulaUnavailable("source_error", (cell.reference,))
    if cell.value_type in ("date", "datetime", "formula_date", "formula_datetime") and isinstance(value, str):
        try:
            return datetime.fromisoformat(value) if "T" in value else date.fromisoformat(value)
        except ValueError:
            raise FormulaUnavailable("source_error", (cell.reference,)) from None
    return value
