from datetime import date, datetime

from openpyxl.worksheet.formula import ArrayFormula, DataTableFormula


def formula_text(value: object) -> str | None:
    if isinstance(value, str) and value.startswith("="):
        return value
    if isinstance(value, ArrayFormula):
        return value.text or "=ARRAY_FORMULA()"
    if isinstance(value, DataTableFormula):
        return "=DATA_TABLE()"
    return None


def safe_indexed_value(
    value: object, formula: str | None
) -> tuple[str | int | float | bool | None, str]:
    if formula:
        return value if isinstance(value, (str, int, float, bool)) else None, "formula"
    if value is None:
        return None, "blank"
    if isinstance(value, bool):
        return value, "boolean"
    if isinstance(value, datetime):
        return value.isoformat(), "datetime"
    if isinstance(value, date):
        return value.isoformat(), "date"
    if isinstance(value, (int, float)):
        return value, "number"
    if isinstance(value, str):
        return value, "text"
    return None, "unsupported"
