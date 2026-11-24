"""The groups a table calculation shows: ordered, picked, named, totalled or compared between periods."""
import re
from statistics import mean

from app.agent.query.gpt_calc_filters import WEEKDAYS, _number


_OPS = {"gt": lambda a, b: a > b, "ge": lambda a, b: a >= b, "lt": lambda a, b: a < b, "le": lambda a, b: a <= b,
        "eq": lambda a, b: abs(a - b) < 1e-9, "ne": lambda a, b: abs(a - b) >= 1e-9}


def picked(calc, values, period_position=None):
    """(items in the order shown, the groups' mean when the pick compares with it, the place asked by rank_of)."""
    days = {name: number for number, name in enumerate(WEEKDAYS)}
    items = sorted(values.items(), key=lambda item: tuple(days.get(part, part) for part in item[0])) \
        if calc.period != "none" else list(values.items())  # months, or 월요일 … 일요일, in order
    if calc.versus_previous != "none":  # 전월 대비: each period against the one before it, within each store
        other = (lambda key: key[1 - period_position]) if period_position is not None and len(items[0][0]) == 2 \
            else (lambda key: key[:-1] if len(key) > 1 and period_position is None else ())
        series = {}
        for key, value in items:
            series.setdefault(other(key), []).append((key, value))
        items = [(key, value - before if calc.versus_previous == "difference" else (value - before) / abs(before) * 100)
                 for points in series.values() for (_, before), (key, value) in zip(points, points[1:])
                 if calc.versus_previous == "difference" or before]
    if calc.having is not None:  # 5번 이상 거래한 고객: groups whose value meets the condition
        items = [item for item in items if _OPS[calc.having.op](item[1], calc.having.value)]
    if calc.order != "none" and not (calc.period != "none" and calc.pick == "all" and calc.versus_previous == "none"):
        items.sort(key=lambda item: item[1], reverse=calc.order == "desc")
    place = _place(calc, items)
    middle = mean(value for _, value in items) if calc.pick in {"above_mean", "below_mean"} else None
    if calc.pick in {"nth", "top"} and max(calc.n, 1) == 1 and len(items) == 2 and calc.order != "none":
        return items, middle, place  # "평일과 주말 중 높은 쪽": both shown, the higher first
    if calc.pick in {"nth", "top"}:  # a group tied with the last one picked is picked too
        n = max(calc.n, 1)
        last = items[n - 1][1] if n <= len(items) else None
        items = [] if last is None else [item for number, item in enumerate(items) if item[1] == last and number >= n - 1
                                          or calc.pick == "top" and number < n]
    elif middle is not None:
        items = [item for item in items if (item[1] > middle if calc.pick == "above_mean" else item[1] < middle)]
    return items, middle, place


def _place(calc, items):
    """(place, of how many, value) of the group rank_of names, ties sharing the higher place; else None."""
    if not calc.rank_of:
        return None
    wanted = " ".join(calc.rank_of.split()).casefold()
    parts = lambda key: {" ".join(part.split()).casefold() for item in key for part in str(item).split(" · ")}  # noqa: E731
    found = [value for key, value in items if wanted in parts(key)]
    if not found:
        return None
    ahead = sum(1 for _, value in items if (value > found[0] if calc.order != "asc" else value < found[0]))
    tied = sum(1 for _, value in items if value == found[0]) > 1  # 라면 and 선풍기 both 6,000: 공동 10위
    return ahead + 1, len(items), found[0], tied


def then_value(calc, items):
    """The sum or mean of the groups shown: 상위 3일의 평균, 월별 합계의 평균(월평균)."""
    if calc.then == "none" or len(items) < 2 or calc.pick not in {"top", "nth"} and calc.period == "none":
        return None  # only the picked groups (상위 3일) or periods (월별 합계의 월평균) are taken together
    numbers = [value for _, value in items]
    return calc.then, sum(numbers) if calc.then == "sum" else mean(numbers)


def holders(calc, key, value, derived, name):
    """The names of the rows holding a group's largest or smallest value: 1반's top score is 조서아's."""
    if name is None or calc.aggregate not in {"max", "min"}:
        return ""
    names = [str(row.values.get(name.id)) for row, found in derived.get(key, []) if _number(found) and found == value]
    return ", ".join(dict.fromkeys(names))


def changes(calc, values, period_position):
    """Each category's first and last period with their values: (category, first, a, last, b)."""
    if not calc.change or period_position is None or len(calc.group_by) != 2:
        return ()
    other = 1 - period_position
    series = {}
    for key, value in values.items():
        series.setdefault(key[other], []).append((key[period_position], value))
    found = []
    for category, points in series.items():
        points.sort()
        if len(points) >= 2:
            (first, a), (last, b) = points[0], points[-1]
            found.append((category, first, a, last, b))
    if calc.order != "none":
        rate = lambda item: (item[4] - item[2]) / abs(item[2]) if item[2] else 0  # noqa: E731
        found.sort(key=rate, reverse=calc.order == "desc")
    return tuple(found)


def column_totals(calc, items, buckets, measure, added, name_of):
    """(column, value) of one group's columns added together: Q1 … Q4, Mid-2011 … Mid-2024."""
    if not added or len(items) != 1 or calc.aggregate != "sum":
        return ()
    return tuple((name_of(column), sum(value for row in buckets[items[0][0]] if _number(value := row.values.get(column.id))))
                 for column in [measure, *added])


def named_periods(calc, groups, values, position):
    """전년 대비 over a column naming its periods ('FY20' · 'FY21', '2023년'): the groups in their order."""
    if calc.versus_previous == "none" or position is not None or groups != 1 or not all(
            re.search(r"\d", key[0]) for key in values):
        return values, position
    natural = lambda label: [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", label)]  # noqa: E731
    return dict(sorted(values.items(), key=lambda item: natural(item[0][0]))), 0
