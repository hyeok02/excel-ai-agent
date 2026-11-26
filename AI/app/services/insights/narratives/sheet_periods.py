"""Sheets of one layout named by their periods ('2022년', '2023년'): the first and last compared.

Each sheet holds one table with the same header and the same items, so its totals and each item's
values are read across the sheets in the order of the years their names carry. A sheet written in 원 and
the next in 만원 are put in one unit first: 60,000원 and 6만원 are the same amount, not a 100% fall.
"""
import re

from app.services.insights.narratives.layout_tables import (
    NONADDITIVE, WON, amount, change, heading, kept_rows, noted, label, numbers, sheet_tables, span, texts,
)
from app.services.insights.narratives.narrative_values import insight, subject_particle, topic_particle
from app.services.insights.narratives.sheet_records import record_totals

_YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_MONEY = re.compile(r"\b(?:amount|revenue|sales|cost)\b|금액|매출|비용", re.I)


_MONTHS = {name: number for number, names in enumerate((
    ("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"), ("may",), ("june", "jun"),
    ("july", "jul"), ("august", "aug"), ("september", "sep", "sept"), ("october", "oct"),
    ("november", "nov"), ("december", "dec")), 1) for name in names}


def _period(name):
    """('year', 2023) of '2023년', ('month', 3) of '3월' or 'March', else None."""
    if year := _YEAR.search(name):
        return "year", int(year[1])
    if month := re.fullmatch(r"\s*(1[0-2]|[1-9])\s*월\s*", name):
        return "month", int(month[1])
    found = _MONTHS.get(name.strip().casefold())
    return ("month", found) if found else None


def sheet_period_report(context):
    found = []
    for sheet in context.get("sheets", []):
        period = _period(str(sheet.get("name", "")))
        tables = sheet_tables(sheet) if period else []
        if len(tables) == 1:
            found.append((period, tables[0]))
    if len({period for period, _ in found}) != len(found) or len(found) < 2 or len({p[0] for p, _ in found}) != 1:
        return [], ""
    found.sort(key=lambda item: item[0])
    shape = lambda table: [label(table, p) for p in sorted(table["header"][-1])]  # noqa: E731
    if any(len(table["header"]) != 1 for _, table in found):
        return [], ""
    if any(shape(table) != shape(found[0][1]) for _, table in found):
        return record_totals([table for _, table in found])  # January has 16 columns, February 17
    first, last = found[0][1], found[-1][1]
    key = min(first["header"][-1])
    rows = {id(table): kept_rows(table, key) for _, table in found}
    names = {id(table): texts(rows[id(table)], key) for _, table in found}
    if any(not value or len(set(value)) != len(value) for value in names.values()):
        return record_totals([table for _, table in found])  # records, not the same items again
    shared = [name for name in names[id(first)] if name in names[id(last)]]
    if len(shared) < 2 or len(shared) < 0.8 * max(len(names[id(first)]), len(names[id(last)])):
        return record_totals([table for _, table in found])
    measures = [p for p in sorted(first["header"][-1]) if p != key and not NONADDITIVE.search(label(first, p))
                and all(numbers(rows[id(table)], p) for _, table in found)]
    if not measures:
        return [], ""
    scale, unit = _units([table for _, table in found])
    value = lambda table, p: [v * scale[id(table)] for v in numbers(rows[id(table)], p)]  # noqa: E731
    before, after = first["sheet"], last["sheet"]
    cited = lambda p: [heading(first, p), span(first, rows[id(first)], p), heading(last, p),  # noqa: E731
                       span(last, rows[id(last)], p), span(first, rows[id(first)], key),
                       span(last, rows[id(last)], key)]
    items, rates = [], []
    for p in measures[:2]:
        what = label(first, p)
        old, new = sum(value(first, p)), sum(value(last, p))
        total = change(old, new)
        fact = noted(f"{what} 합계는 ‘{before}’ {total.replace('에서 ', f'에서 ‘{after}’ ', 1)}.", unit)
        items.append(insight(f"{what} 합계 비교 ({before}→{after})", fact, cited(p), "change", topic=what))
        if old and new != old:
            rates.append(f"{what} 합계는 {abs(new - old) / abs(old) * 100:.1f}% {'증가' if new > old else '감소'}")
    chosen = next((p for p in measures if _MONEY.search(label(first, p))), measures[0])
    items.append(_items((first, last, unit), rows, key, shared, (chosen, value), cited(chosen)))
    if not rates:
        return items, items[-1].fact
    said = ", ".join(rates)
    return items, f"‘{before}’ 대비 ‘{after}’ {said}했습니다."


def _units(tables):
    """(scale per table, unit said): tables counted in 원 and 만원, or 개 and 만개, put in the smaller unit."""
    units = [table["unit"].replace(" ", "") for table in tables]
    read = [re.fullmatch(r"(십만|백만|천만|십|백|천|만|억|조)?(\D{1,4})", unit) for unit in units]
    if len(set(units)) == 1 or not all(read) or len({found[2] for found in read}) != 1:
        return {id(table): 1 for table in tables}, tables[0]["unit"]
    scale = [WON.get(f"{found[1] or ''}원", 1) for found in read]  # the same steps as 원: 만개 is 10,000개
    base = min(range(len(tables)), key=lambda at: scale[at])
    return {id(table): scale[at] / scale[base] for at, table in enumerate(tables)}, units[base]


def _items(sides, rows, key, shared, measure, cited):
    (first, last, unit), (p, read) = sides, measure
    value = lambda table: dict(zip(texts(rows[id(table)], key), read(table, p)))  # noqa: E731
    old, new = value(first), value(last)
    moves = {name: new[name] - old[name] for name in shared}
    up, down = sum(move > 0 for move in moves.values()), sum(move < 0 for move in moves.values())
    what, kind = label(first, p), label(first, key)
    if not up and not down:  # the same amounts in both (60,000원 and 6만원)
        fact = noted(f"{kind}별 {what}{topic_particle(what)} {len(moves)}개 모두 변동이 없습니다.", unit)
        return insight(f"{kind}별 {what} 변화", fact, cited, "change", topic=what)
    if down == len(moves) or up == len(moves):
        trend = f"{kind}별 {what}{topic_particle(what)} {len(moves)}개 모두 {'감소' if down else '증가'}했고"
    else:
        trend = f"{kind}별 {what}{topic_particle(what)} {up}개 증가, {down}개 감소했고"
    name = max(moves, key=lambda item: abs(moves[item]))
    said = change(old[name], new[name], ending="해")
    fact = noted(f"{trend}, {name}{subject_particle(name)} {said} 변화 폭이 가장 큽니다.", unit)
    return insight(f"{kind}별 {what} 변화", fact, cited, "change", topic=what)

