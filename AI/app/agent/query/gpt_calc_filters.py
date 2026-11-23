"""Row conditions of a GPT-chosen table calculation: values, dates, periods and other columns."""
import calendar
import re
from datetime import date, datetime

_ALTERNATIVE = {"eq", "contains", "year", "month", "quarter"}
_number = lambda value: isinstance(value, (int, float)) and not isinstance(value, bool)  # noqa: E731


_MONTHS = {name.casefold(): number for names in (calendar.month_name, calendar.month_abbr)
           for number, name in enumerate(names) if name} | {"sept": 9}


def _month_text(value):
    """'December 2025', 'Dec-2025', '2025년 12월', '2025.12' or '2025/12' as 2025-12; else None."""
    text = value.strip()
    if found := re.fullmatch(r"([A-Za-z]{3,9})\.?[\s\-]+(\d{4})", text):
        number = _MONTHS.get(found.group(1).casefold())
        return f"{found.group(2)}-{number:02d}" if number else None
    if found := re.match(r"(\d{4})\s*(?:년\s*|[./]\s*)(\d{1,2})(?:\s*월|\b)", text):
        return f"{found.group(1)}-{int(found.group(2)):02d}" if 1 <= int(found.group(2)) <= 12 else None
    return None


def _date_part(value, period):
    if isinstance(value, (datetime, date)):
        text = value.isoformat()
    elif isinstance(value, str) and re.match(r"\d{4}-\d{2}", value):
        text = value
    elif not isinstance(value, str) or (text := _month_text(value)) is None:
        return None
    if period == "quarter":
        return f"{text[:4]}-Q{(int(text[5:7]) - 1) // 3 + 1}"
    if period == "half":  # 상반기 / 하반기
        return f"{text[:4]}-H{1 if int(text[5:7]) <= 6 else 2}"
    if period == "weekday":  # 요일: a day is needed
        try:
            return WEEKDAYS[date.fromisoformat(text[:10]).weekday()]
        except ValueError:
            return None
    return text[:4] if period == "year" else text[:7]


WEEKDAYS = ("월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일")
LISTED = "\x1f"  # the values of another table's column, for in / not_in


def _matches(value, item, row=None, other=None):
    op, wanted = item.op, item.value.strip()
    # "2025-03-15T23:59:59" or "2025-03-15 00:00:00Z" bounds the day 2025-03-15
    wanted = re.sub(r"^(\d{4}-\d{2}-\d{2})[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?Z?$", r"\1", wanted)
    if op.endswith("_column"):  # 재고수량 < 안전재고: two values of one row
        compared = row.values.get(other.id) if row is not None and other is not None else None
        return _number(value) and _number(compared) and {"gt_column": value > compared, "ge_column": value >= compared,
                                                         "lt_column": value < compared, "le_column": value <= compared}[op]
    if op in {"in", "not_in"}:  # 거래가 없는 고객: the customer's ID among another table's IDs
        found = " ".join(str(value if value is not None else "").split()).casefold() in {
            " ".join(part.split()).casefold() for part in item.value.split(LISTED)}
        return found if op == "in" else not found
    if op in {"year", "month", "quarter"}:  # "2022-12T00:00:00Z" names the month 2022-12
        wanted = wanted[:{"year": 4, "month": 7}[op]] if op != "quarter" and re.match(r"\d{4}-\d{2}", wanted) else wanted
        return _date_part(value, op) == wanted.upper()
    if op in {"gt", "ge", "lt", "le"} and (moment := _moment(value, wanted)) is not None:
        found, limit = moment  # "2020년 이후 입사": a date against a year, year-month or day
        return {"gt": found > limit, "ge": found >= limit, "lt": found < limit, "le": found <= limit}[op]
    if op in {"gt", "ge", "lt", "le"}:
        try:
            limit = float(wanted.replace(",", ""))
        except ValueError:
            return False
        return _number(value) and {"gt": value > limit, "ge": value >= limit,
                                   "lt": value < limit, "le": value <= limit}[op]
    text = " ".join(str(value if value is not None else "").split()).casefold()
    if op == "contains":
        return wanted.casefold() in text
    same = text == wanted.casefold() or _number(value) and _same_number(value, wanted)
    return same if op == "eq" else not same


def _same_number(value, wanted):
    try:
        return abs(float(wanted.replace(",", "")) - value) < 1e-9
    except ValueError:
        return False


def _moment(value, wanted):
    """(the date's part, the limit) when a date is compared with 2020, 2020-03 or 2020-03-05; else None."""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, str) and (text := re.match(r"(\d{4})-(\d{2})-(\d{2})", value.strip()) or
                                   re.fullmatch(r"(\d{4})-(\d{2})", _month_text(value) or "")):
        value = date(*(int(part) for part in text.groups()), *([] if len(text.groups()) == 3 else [1]))
    if not isinstance(value, date) or not (found := re.fullmatch(r"(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?", wanted)):
        return None
    parts = tuple(int(part) for part in found.groups() if part)
    return (value.year, value.month, value.day)[:len(parts)], parts
