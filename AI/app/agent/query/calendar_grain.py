"""Whether a ranking groups days where the question asks for months, quarters, years or weekdays.

"2023년 판매금액이 가장 높은 달은?" grouped by the Date column ranks single days; its answer
is a day, not a month. Such a ranking is not given; a calculation by month answers instead.
"""
import re
from datetime import date, datetime

_GRAIN = re.compile(r"달|월별|분기|반기|요일|주말|평일|연도|년도|어느\s*해|몇\s*년|"
                    r"\b(?:month|quarter|year|weekday|weekend|day of the week)", re.I)
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")


def day_groups(question, table, column_id):
    """True when the question names a calendar grain and the grouped column holds dates."""
    if not _GRAIN.search(question):
        return False
    values = [row.values.get(column_id) for row in table.rows[:50] if row.values.get(column_id) not in (None, "")]
    return bool(values) and all(isinstance(value, (date, datetime)) or isinstance(value, str) and _DAY.match(value)
                                for value in values)
