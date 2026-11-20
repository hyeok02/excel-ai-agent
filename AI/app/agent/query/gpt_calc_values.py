"""Values of a table calculation's rows: group names, row names and differences, dates included."""
from datetime import date, datetime, time

from app.agent.query.gpt_calc_filters import _number


def _row_name(table, row, measure):
    """A row ranked by itself is named by its other values: 2024-12-09 · 월 · 홍대점."""
    return " · ".join(_label(value) for column in table.columns if column is not measure
                      and (value := row.values.get(column.id)) not in (None, "") and not _number(value)) or str(row.row_number)


def _minus(value, other):
    """value - other for numbers; the days between two dates."""
    if _number(value) and _number(other):
        return value - other
    def day(moment):
        if isinstance(moment, str) and len(moment) >= 10 and moment[4] == "-" and moment[7] == "-":
            try:
                moment = datetime.fromisoformat(moment[:10])
            except ValueError:
                return None
        return moment.date() if isinstance(moment, datetime) else moment if isinstance(moment, date) else None
    first, second = day(value), day(other)
    return (first - second).days if first is not None and second is not None else None


def _label(value):
    """A group's name as written: a day without a time is 2024-10-21, not 2024-10-21T00:00:00."""
    if isinstance(value, datetime) and value.time() == time():
        value = value.date()
    text = "빈칸" if value is None else " ".join(str(value).split())
    return text.removesuffix("T00:00:00") if len(text) == 19 and text[10:] == "T00:00:00" else text
