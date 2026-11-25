from datetime import date, datetime, time

from app.services.workbook_details.cell_values import formula_text


def safe_indexed_value(
    value: object, formula: str | None
) -> tuple[str | int | float | bool | None, str]:
    if formula:
        if isinstance(value, datetime):
            return value.isoformat(), "formula_datetime"
        if isinstance(value, date):
            return value.isoformat(), "formula_date"
        if isinstance(value, time):
            return value.isoformat(), "formula_time"
        return value if isinstance(value, (str, int, float, bool)) else None, "formula"
    if value is None:
        return None, "blank"
    if isinstance(value, bool):
        return value, "boolean"
    if isinstance(value, datetime):
        return value.isoformat(), "datetime"
    if isinstance(value, date):
        return value.isoformat(), "date"
    if isinstance(value, time):  # 10:00 in a Time column, as the summary reads it
        return value.isoformat(), "time"
    if isinstance(value, (int, float)):
        return value, "number"
    if isinstance(value, str):
        return value, "text"
    return None, "unsupported"
