"""The groups a table calculation shows: ordered, picked, named, totalled or compared between periods."""
from statistics import mean

from app.agent.query.gpt_calc_filters import _number


def picked(calc, values):
    """(items in the order shown, the groups' mean when the pick compares with it)."""
    items = sorted(values.items()) if calc.period != "none" else list(values.items())  # months in order
    if calc.order != "none" and not (calc.period != "none" and calc.pick == "all"):
        items.sort(key=lambda item: item[1], reverse=calc.order == "desc")
    middle = mean(value for _, value in items) if calc.pick in {"above_mean", "below_mean"} else None
    if calc.pick in {"nth", "top"}:  # a group tied with the last one picked is picked too
        n = max(calc.n, 1)
        last = items[n - 1][1] if n <= len(items) else None
        items = [] if last is None else [item for number, item in enumerate(items) if item[1] == last and number >= n - 1
                                          or calc.pick == "top" and number < n]
    elif middle is not None:
        items = [item for item in items if (item[1] > middle if calc.pick == "above_mean" else item[1] < middle)]
    return items, middle


def then_value(calc, items):
    """The sum or mean of the groups shown: 상위 3일의 평균, 월별 합계의 평균(월평균)."""
    if calc.then == "none" or len(items) < 2 and calc.pick not in {"top", "nth"} or calc.pick not in {"top", "nth"} \
            and calc.period == "none":
        return None  # only the picked groups (상위 3일) or periods (월별 합계의 월평균) are taken together
        return None
    numbers = [value for _, value in items]
    return sum(numbers) if calc.then == "sum" else mean(numbers)


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
