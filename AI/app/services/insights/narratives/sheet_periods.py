"""Sheets of one layout named by their periods ('2022년', '2023년'): the first and last compared.

Each sheet holds one table with the same header and the same items, so its totals and each item's
values are read across the sheets in the order of the years their names carry.
"""
import re

from app.services.insights.narratives.layout_tables import (
    NONADDITIVE, amount, change, heading, kept_rows, noted, label, numbers, sheet_tables, span, texts,
)
from app.services.insights.narratives.narrative_values import insight, subject_particle, topic_particle

_YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")
_MONEY = re.compile(r"\b(?:amount|revenue|sales|cost)\b|금액|매출|비용", re.I)


def sheet_period_report(context):
    found = []
    for sheet in context.get("sheets", []):
        year = _YEAR.search(str(sheet.get("name", "")))
        tables = sheet_tables(sheet) if year else []
        if len(tables) == 1:
            found.append((int(year[1]), tables[0]))
    if len({year for year, _ in found}) != len(found) or len(found) < 2:
        return [], ""
    found.sort(key=lambda item: item[0])
    shape = lambda table: [label(table, p) for p in sorted(table["header"][-1])]  # noqa: E731
    if any(shape(table) != shape(found[0][1]) or len(table["header"]) != 1 for _, table in found):
        return [], ""
    first, last = found[0][1], found[-1][1]
    key = min(first["header"][-1])
    rows = {id(table): kept_rows(table, key) for _, table in found}
    names = {id(table): texts(rows[id(table)], key) for _, table in found}
    if any(not value or len(set(value)) != len(value) for value in names.values()):
        return [], ""
    shared = [name for name in names[id(first)] if name in names[id(last)]]
    if len(shared) < 2 or len(shared) < 0.8 * max(len(names[id(first)]), len(names[id(last)])):
        return [], ""
    measures = [p for p in sorted(first["header"][-1]) if p != key and not NONADDITIVE.search(label(first, p))
                and all(numbers(rows[id(table)], p) for _, table in found)]
    if not measures:
        return [], ""
    before, after = first["sheet"], last["sheet"]
    cited = lambda p: [heading(first, p), span(first, rows[id(first)], p), heading(last, p),  # noqa: E731
                       span(last, rows[id(last)], p), span(first, rows[id(first)], key),
                       span(last, rows[id(last)], key)]
    items, rates = [], []
    for p in measures[:2]:
        what = label(first, p)
        old, new = sum(numbers(rows[id(first)], p)), sum(numbers(rows[id(last)], p))
        total = change(old, new)
        fact = noted(f"{what} 합계는 ‘{before}’ {total.replace('에서 ', f'에서 ‘{after}’ ', 1)}.", first["unit"])
        items.append(insight(f"{what} 합계 비교 ({before}→{after})", fact, cited(p), "change", topic=what))
        if old and new != old:
            rates.append(f"{what} 합계는 {abs(new - old) / abs(old) * 100:.1f}% {'증가' if new > old else '감소'}")
    chosen = next((p for p in measures if _MONEY.search(label(first, p))), measures[0])
    items.append(_items(first, last, rows, key, shared, chosen, cited(chosen)))
    if not rates:
        return items, items[-1].fact
    said = ", ".join(rates)
    return items, f"‘{before}’ 대비 ‘{after}’ {said}했습니다."


def _items(first, last, rows, key, shared, p, cited):
    value = lambda table: dict(zip(texts(rows[id(table)], key), numbers(rows[id(table)], p)))  # noqa: E731
    old, new = value(first), value(last)
    moves = {name: new[name] - old[name] for name in shared}
    up, down = sum(move > 0 for move in moves.values()), sum(move < 0 for move in moves.values())
    what, kind = label(first, p), label(first, key)
    if down == len(moves) or up == len(moves):
        trend = f"{kind}별 {what}{topic_particle(what)} {len(moves)}개 모두 {'감소' if down else '증가'}했고"
    else:
        trend = f"{kind}별 {what}{topic_particle(what)} {up}개 증가, {down}개 감소했고"
    name = max(moves, key=lambda item: abs(moves[item]))
    said = change(old[name], new[name], ending="해")
    fact = noted(f"{trend}, {name}{subject_particle(name)} {said} 변화 폭이 가장 큽니다.", first["unit"])
    return insight(f"{kind}별 {what} 변화", fact, cited, "change", topic=what)

