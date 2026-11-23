"""Values of a table calculation's rows: group names, row names and differences, dates included."""
import ast
import re
from datetime import date, datetime, time

from app.agent.query.gpt_calc_cells import _evaluate
from app.agent.query.gpt_calc_filters import _number


def _row_name(table, row, measure):
    """A row ranked by itself is named by its other values: 2024-12-09 · 월 · 홍대점."""
    return " · ".join(_label(value) for column in table.columns if column is not measure
                      and (value := row.values.get(column.id)) not in (None, "") and not _number(value)) or str(row.row_number)


def as_day(moment):
    """A date cell (or its ISO text) as a date; else None."""
    if isinstance(moment, str) and len(moment) >= 10 and moment[4] == "-" and moment[7] == "-":
        try:
            moment = datetime.fromisoformat(moment[:10])
        except ValueError:
            return None
    return moment.date() if isinstance(moment, datetime) else moment if isinstance(moment, date) else None


def _minus(value, other):
    """value - other for numbers; the days between two dates."""
    if _number(value) and _number(other):
        return value - other
    first, second = as_day(value), as_day(other)
    return (first - second).days if first is not None and second is not None else None


_LETTER = re.compile(r"\[([A-Za-z]{1,3})\]")


def row_formula(table, text):
    """(columns read, the value of a row) for arithmetic over a row's columns: [G]*[H]*(1-[I]); else None."""
    by_id = {column.id.upper(): column for column in table.columns}
    text = re.sub(r"DATEDIF\s*\(\s*(\[[A-Za-z]{1,3}\])\s*,\s*(\[[A-Za-z]{1,3}\])\s*,\s*\"?[Dd]\"?\s*\)", r"(\2-\1)",
                  text or "", flags=re.I)  # Excel's days between two dates
    letters = list(dict.fromkeys(letter.upper() for letter in _LETTER.findall(text or "")))
    expression = re.sub(r"\babs\s*\(", "abs(", _LETTER.sub(lambda match: f"c_{match.group(1).upper()}", text or ""),
                        flags=re.I).replace("^", "**")
    if not letters or any(letter not in by_id for letter in letters) or re.search(
            r"(?!abs\()\b[A-Za-z_]\w*\s*\(|//|%", expression):  # arithmetic, powers and abs() only
        return None
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError:
        return None
    columns = [by_id[letter] for letter in letters]

    def value(row):  # a date reads as its day number, so [E]-[D] is the days between them
        names = {f"c_{column.id.upper()}": day.toordinal() if not _number(cell := row.values.get(column.id))
                 and (day := as_day(cell)) else cell for column in columns}
        try:
            return float(_evaluate(tree, names)) if all(_number(item) for item in names.values()) else None
        except (ZeroDivisionError, ValueError, TypeError):
            return None
    return columns, value


def _label(value):
    """A group's name as written: a day without a time is 2024-10-21, not 2024-10-21T00:00:00."""
    if isinstance(value, datetime) and value.time() == time():
        value = value.date()
    text = "빈칸" if value is None else " ".join(str(value).split())
    return text.removesuffix("T00:00:00") if len(text) == 19 and text[10:] == "T00:00:00" else text


def with_date_group(table, groups, period):
    """A period asked of groups that hold no date (월별 by 매장 alone) gets the table's one date column added."""
    from app.agent.query.gpt_calc_filters import _date_part
    dated = lambda column: any(_date_part(row.values.get(column.id), "month") for row in table.rows[:20])  # noqa: E731
    if period == "none" or None in groups or any(dated(column) for column in groups):
        return groups
    found = [column for column in table.columns if dated(column)]
    return [*groups, found[0]] if len(found) == 1 else groups
