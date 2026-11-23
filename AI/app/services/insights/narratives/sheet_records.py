"""Record lists kept one sheet per period ('January', 'February', 'March'): each period's totals compared.

The rows are different records in every sheet, so only the columns all sheets share are added up, and only
amounts and quantities (Total, Quantity, 금액, 수량): a price, a rate or a rating is never a sum.
"""
import re

from app.services.insights.narratives.layout_tables import NONADDITIVE, amount, change, heading, label, span
from app.services.insights.narratives.narrative_values import finite, insight

_ADDED = re.compile(r"\b(?:total|amount|revenue|sales|quantity|qty|units)\b|금액|매출|수량|판매량|건수", re.I)
_SCORE = re.compile(r"\b(?:rating|score|grade)\b|평점|점수|등급", re.I)


def record_totals(tables):
    columns = [{label(table, p): p for p in table["header"][-1]} for table in tables]
    shared = [name for name in columns[0] if all(name in found for found in columns[1:])]
    totals = []
    for name in shared:
        if not _ADDED.search(name) or NONADDITIVE.search(name) or _SCORE.search(name):
            continue
        cells = [[row.get(found[name], {}) for row in table["rows"]] for table, found in zip(tables, columns)]
        values = [[float(cell["value"]) for cell in column if finite(cell.get("value"))] for column in cells]
        if all(values) and all(min(column) >= 0 for column in values):
            totals.append((name, [sum(column) for column in values]))
    if not totals:
        return [], ""
    sheets = [table["sheet"] for table in tables]
    items, rates = [], []
    for name, sums in totals[:2]:
        listed = ", ".join(f"‘{sheet}’ {amount(total)}" for sheet, total in zip(sheets, sums))
        fact = f"{name} 합계는 {listed}입니다."
        if len(sums) > 2:
            fact += f" ‘{sheets[0]}’ {change(sums[0], sums[-1]).replace('에서 ', f'에서 ‘{sheets[-1]}’ ', 1)}."
        elif sums[0]:
            fact = f"{name} 합계는 ‘{sheets[0]}’ {change(*sums).replace('에서 ', f'에서 ‘{sheets[-1]}’ ', 1)}."
        cited = [ref for table, found in zip(tables, columns) for ref in
                 (heading(table, found[name]), span(table, table["rows"], found[name]))]
        items.append(insight(f"{name} 합계 비교 ({sheets[0]}→{sheets[-1]})", fact, cited, "change", topic=name))
        if sums[0] and sums[-1] != sums[0]:
            rates.append(f"{name} 합계는 {abs(sums[-1] - sums[0]) / abs(sums[0]) * 100:.1f}% "
                         f"{'증가' if sums[-1] > sums[0] else '감소'}")
    if not rates:
        return items, items[0].fact
    return items, f"‘{sheets[0]}’ 대비 ‘{sheets[-1]}’ {', '.join(rates)}했습니다."
