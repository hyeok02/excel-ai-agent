"""What a record list's columns are, read from their values rather than their header words.

A column is a key when every record holds a different text in it ("프로젝트명", "응답자ID"),
or, for daily records per category, when the date and a category column together are unique.
A numeric column is a total-able quantity when its values are non-negative and reach past
the bounded scales of scores and ratings (1~5, 0~100): 방문자수, 재고수량, 예산.
"""
import re
from itertools import combinations

_DATE = re.compile(r"\d{4}-\d{2}(?:-\d{2}|$)")  # a day, or a month written 2024-07
SCALE = 100
MIN_RECORDS = 10  # fewer rows with unique labels are a summary table (Category | Value), not records


def data_keys(headers, records):
    """Columns that tell every record apart, by their values: unique texts, else a date with a category."""
    def texts(p):
        return [row.get(p, {}).get("value") for row in records]
    if len(records) < MIN_RECORDS:
        return []
    unique = [p for p in headers if all(isinstance(v, str) and v.strip() for v in texts(p))
              and len(set(texts(p))) == len(records) and not all(_DATE.match(v) for v in texts(p))]
    if unique:
        return unique[:1]
    for p in headers:
        if all(isinstance(v, str) and _DATE.match(v) for v in texts(p)):
            labels = [q for q in headers if q != p and all(isinstance(v, str) and v.strip() for v in texts(q))
                      and 2 <= len(set(texts(q))) < len(records)]
            for size in (1, 2):  # a date per store, or per store and item
                for chosen in combinations(labels, size):
                    if len(set(zip(texts(p), *(texts(q) for q in chosen)))) == len(records):
                        return [p]  # the date keys each category's record
    return []


def dated(records, key):
    """Records keyed by a date: daily or monthly flows (입고, 출고, 방문자수) rather than scores."""
    return all(_DATE.match(str(row.get(key, {}).get("value", ""))) for row in records)


def additive_quantity(values, flows=False):
    """Non-negative numbers beyond a score or rating scale, not years and not a running number.

    Dated records hold flows: any size adds up, and a signed net change (순증감) too.
    """
    numbers = [float(value) for value in values]
    if not numbers or not flows and (min(numbers) < 0 or max(numbers) <= SCALE):
        return False
    if all(value.is_integer() and 1900 <= value <= 2100 for value in numbers):
        return False  # years
    ordered = sorted(numbers)
    return not (len(set(numbers)) == len(numbers) and all(b - a == 1 for a, b in zip(ordered, ordered[1:])))


def monthly_totals(sheet, headers, records, key, measure, label, units, record_value, reference, insight):
    """Daily records summed by calendar month (9월 71,857 → 10월 77,386), when the key is a date."""
    dates = [str(row.get(key, {}).get("value", "")) for row in records]
    if not all(_DATE.match(value) for value in dates):
        return None
    _, p, _, cells, values, *_ = measure
    months = {}
    for day, value in zip(dates, values):
        months[day[:7]] = months.get(day[:7], 0) + value
    if not 2 <= len(months) <= 24:
        return None
    ordered = sorted(months.items())
    written = ", ".join(f"{int(month[:4])}년 {int(month[5:])}월 {record_value(total, units)}" for month, total in ordered)
    fact = f"월별 {label} 합계는 {written}입니다."
    evidence = [reference(sheet, headers[p]["cell"]), reference(sheet, headers[key]["cell"]),
                reference(sheet, f"{cells[0]['cell']}:{cells[-1]['cell']}"),
                reference(sheet, f"{records[0][key]['cell']}:{records[-1][key]['cell']}")]
    return insight(f"월별 {label} 합계", fact, evidence, "trend", topic=label)
