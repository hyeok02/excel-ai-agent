"""An amount column read apart by a two- or three-way column: 수입 and 지출 are not added together.

"구분 | 분류 | 금액" records: the totals of each 구분, the largest 구분 split by 분류, and its months.
"""
import re

from app.services.insights.narratives.layout_tables import (
    NONADDITIVE, amount, heading, noted, label, numbers, span, texts,
)
from app.services.insights.narratives.narrative_values import insight, subject_particle, topic_particle

_AMOUNT = re.compile(r"\b(?:amount|total|revenue|sales|cost|expense|value)\b|금액|매출|비용|지출액|수입액|거래액", re.I)
_MONTH = re.compile(r"^(\d{4})[.\-/](\d{1,2})(?:[.\-/]\d{1,2})?(?:$|[T\s])")
MIN_ROWS = 10


def split_report(table):
    rows = table["rows"]
    if len(rows) < MIN_ROWS:
        return None
    positions = sorted({position for row in rows for position in row})
    measure = next((p for p in positions if _AMOUNT.search(label(table, p)) and not NONADDITIVE.search(
        label(table, p)) and (values := numbers(rows, p)) and min(values) >= 0), None)
    groups = {p: values for p in positions if p != measure and (values := texts(rows, p))}
    split = next((p for p, values in groups.items() if 2 <= len(set(values)) <= 3
                  and min(values.count(v) for v in set(values)) >= 2), None)
    if measure is None or split is None:
        return None
    sizes = numbers(rows, measure)
    names = groups[split]
    totals = {name: sum(v for v, n in zip(sizes, names) if n == name) for name in dict.fromkeys(names)}
    unit = table["unit"]
    what, by = label(table, measure), label(table, split)
    ordered = sorted(totals.items(), key=lambda item: -item[1])
    cited = [heading(table, split), span(table, rows, split), heading(table, measure), span(table, rows, measure)]
    listed = ", ".join(f"{name} {amount(total, unit)}" for name, total in ordered)
    fact = f"{by}별 {what} 합계는 {listed}입니다."
    if len(ordered) == 2 and ordered[0][1]:
        fact += f" {ordered[1][0]}{topic_particle(ordered[1][0])} {ordered[0][0]}의 {ordered[1][1] / ordered[0][1] * 100:.1f}%입니다."
    items = [insight(f"{by}별 {what} 합계", noted(fact, unit), cited, "metric", topic=what)]
    busiest = max(totals, key=names.count)
    chosen = [row for row, name in zip(rows, names) if name == busiest]
    detail = next((p for p in groups if p > split and 3 <= len(set(texts(chosen, p) or [])) <= 12
                   and len(set(texts(chosen, p))) <= len(chosen) / 2), None)
    body = f"{by}별 {what} 합계는 {listed}입니다."
    if detail is not None:
        item, largest = _breakdown(table, chosen, busiest, detail, measure, cited)
        items.append(item)
        body = f"{body[:-4]}이며, {busiest} 중에서는 {largest}{subject_particle(largest)} 가장 큽니다."
    if month := _months(table, rows, chosen, busiest, measure, groups, cited):
        items.append(month)
    return items, noted(body, unit)


def _breakdown(table, rows, name, detail, measure, cited):
    values, kinds = numbers(rows, measure), texts(rows, detail)
    totals = {kind: sum(v for v, k in zip(values, kinds) if k == kind) for kind in dict.fromkeys(kinds)}
    whole = sum(totals.values()) or 1
    ordered = sorted(totals.items(), key=lambda item: -item[1])
    unit, what, by = table["unit"], label(table, measure), label(table, detail)
    share = lambda kind, total: f"{amount(total)}({total / whole * 100:.1f}%)"  # noqa: E731
    (top, high), (bottom, low) = ordered[0], ordered[-1]
    fact = (f"{name} {what}{_object(what)} {by} {len(ordered)}개로 나눠 보면 {top}{subject_particle(top)} "
            f"{share(top, high)}로 가장 크고, {bottom}{subject_particle(bottom)} {share(bottom, low)}로 가장 작습니다.")
    return insight(f"{name} {by}별 {what}", noted(fact, unit), [*cited, heading(table, detail),
                   span(table, rows, detail)], "metric", topic=what), top


def _months(table, rows, chosen, name, measure, groups, cited):
    """The months of the largest group, read from a column of dates written 2024.01.25 or 2024-01-25."""
    dated = next((p for p, values in groups.items() if all(_MONTH.match(v) for v in values)), None)
    if dated is None:
        return None
    months = {}
    for row, value in zip(chosen, numbers(chosen, measure)):
        year, month = _MONTH.match(" ".join(str(row[dated]["value"]).split())).groups()
        months[(int(year), int(month))] = months.get((int(year), int(month)), 0) + value
    if len(months) < 3:
        return None
    unit, what = table["unit"], label(table, measure)
    high, low = max(months, key=months.get), min(months, key=months.get)
    top = f"{high[0]}년 {high[1]}월({amount(months[high], unit)})"
    bottom = f"{low[0]}년 {low[1]}월({amount(months[low], unit)})"
    fact = f"월별 {name} {what}{topic_particle(what)} {top}{subject_particle(top)} 가장 많고, {bottom}{subject_particle(bottom)} 가장 적습니다."
    return insight(f"월별 {name} {what}", noted(fact, unit), [*cited, heading(table, dated), span(table, rows, dated)],
                   "trend", topic=what)


def _object(word):
    return "을" if subject_particle(word) == "이" else "를"
