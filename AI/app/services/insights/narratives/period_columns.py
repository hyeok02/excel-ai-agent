"""Columns under a two-row header of years over their parts: '2023 > 상반기, 하반기 | 2024 > ...'.

The parts (반기, 분기, 월) add up to their year, so each year's total is the sum of its columns, and
each item is compared between the first and the last year.
"""
import re

from app.services.insights.narratives.layout_tables import (
    NONADDITIVE, change, heading, kept_rows, noted, label, numbers, span, texts,
)
from app.services.insights.narratives.narrative_values import insight, subject_particle

_YEAR = re.compile(r"^((?:19|20)\d{2})\s*년?$")
_PART = re.compile(r"^(?:상반기|하반기|[1-4]\s*분기|[1-4]\s*Q|Q\s*[1-4]|H\s*[12]|(?:1[0-2]|[1-9])\s*월)$", re.I)


def period_column_report(table):
    if len(table["header"]) != 2 or NONADDITIVE.search(table["title"]):
        return None
    top, parts = table["header"]
    key = min(parts | top)
    years, year = {}, None
    for p in sorted(parts):
        cell = top.get(p)
        if cell and str(cell.get("value") or "").strip():
            found = _YEAR.match(" ".join(str(cell["value"]).split()))
            year = int(found[1]) if found else None
        if year is None or not _PART.match(label(table, p)):
            if p != key:
                return None
            continue
        years.setdefault(year, []).append(p)
    if len(years) < 2 or len({tuple(label(table, p) for p in ps) for ps in years.values()}) != 1:
        return None
    rows = kept_rows(table, key)
    names = texts(rows, key)
    if not names or len(rows) < 2 or any(numbers(rows, p) is None for ps in years.values() for p in ps):
        return None
    first, last = min(years), max(years)
    total = lambda y, row=None: sum(  # noqa: E731
        float(r[p]["value"]) for r in ([row] if row else rows) for p in years[y])
    unit, kind = table["unit"], label(table, key)
    cited = [heading(table, p, 0) for p in (years[first][0], years[last][0])]
    cited += [span(table, rows, p) for p in (*years[first], *years[last])] + [span(table, rows, key)]
    fact = f"연도별 합계는 {first}년 {change(total(first), total(last)).replace('에서 ', f'에서 {last}년 ', 1)}."
    items = [insight(f"연도별 합계 ({first}→{last})", noted(fact, unit), cited, "change")]
    moves = {name: (total(first, row), total(last, row)) for name, row in zip(names, rows)}
    grew = max(moves, key=lambda name: moves[name][1] - moves[name][0])
    fell = min(moves, key=lambda name: moves[name][1] - moves[name][0])
    parts_said = []
    if moves[grew][1] > moves[grew][0]:
        parts_said.append(f"{grew}{subject_particle(grew)} {change(*moves[grew], ending='해')} 가장 많이 늘었고")
    if moves[fell][1] < moves[fell][0]:
        parts_said.append(f"{fell}{subject_particle(fell)} {change(*moves[fell], ending='해')} 가장 많이 줄었습니다")
    if parts_said:
        said = ", ".join(parts_said)
        said = said if said.endswith("다") else said[:-1] + "습니다"
        items.append(insight(f"{kind}별 연도 합계 변화", noted(f"{kind}별로는 {said}.", unit), cited, "change"))
    before, after = total(first), total(last)
    body = f"{first}년 대비 {last}년 합계는 {abs(after - before) / abs(before) * 100:.1f}% " \
           f"{'증가' if after > before else '감소'}했" if before and after != before else f"{first}년과 {last}년 합계는 같았"
    if moves[grew][1] > moves[grew][0]:
        return items, f"{body}고, {grew}{subject_particle(grew)} 가장 많이 늘었습니다."
    return items, f"{body}습니다."

