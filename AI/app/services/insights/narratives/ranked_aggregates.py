"""Aggregate and component facts from a detected ranked-table schema."""
import re
from collections import defaultdict

from app.services.insights.narratives.narrative_values import finite, insight, number, reference
from app.services.insights.narratives.table_schema import share_value

TOTAL = re.compile(r"\b(?:all|total|overall)\b|전체|합계|총합", re.I)


def aggregate_candidates(sheet, records, schema, headers, include_component=True):
    usable = [(row, _get(row, schema, "label"), _get(row, schema, "share"),
               _get(row, schema, "quantity")) for row in records]
    usable = [item for item in usable if item[1] and item[2]
              and isinstance(item[1].get("value"), str) and finite(item[2].get("value"))]
    totals = [item for item in usable if TOTAL.search(str(item[1]["value"]))]
    results = [_metric(sheet, "total", label, share, quantity, headers)
               for _, label, share, quantity in totals]
    components = [item for item in usable if item not in totals]
    if components and include_component:
        _, label, share, quantity = max(components, key=lambda item: share_value(item[2]))
        results.append(_metric(sheet, "component", label, share, quantity, headers))
    if "category" in schema:
        results.extend(_category_totals(sheet, usable, schema))
    return results


def quantity_label(headers):
    source = str(headers.get("quantity", ""))
    return "보유 주식 수" if re.search(r"\bshares?\b|주식", source, re.I) else "수량"


def _category_totals(sheet, usable, schema):
    groups = defaultdict(list)
    for item in usable:
        groups[str(item[1]["value"]).strip()].append(item)
    results = []
    for label, members in groups.items():
        if len(members) < 2 or not _same_scope(members, schema):
            continue
        total = sum(share_value(item[2]) for item in members)
        if not 0 <= total <= 100:
            continue
        cited = [cell for item in members for cell in (item[1], item[2])]
        fact = f"{label} 유형 {len(members)}개 항목의 비중 합계는 {number(total)}%입니다."
        results.append(("aggregate", float(total),
                        insight(f"{label} 구성비 합계", fact, _refs(sheet, cited), "metric")))
    return results


def _metric(sheet, kind, label, share, quantity, headers):
    parts, cited = [], [label]
    if quantity and finite(quantity.get("value")):
        parts.append(f"{quantity_label(headers)}는 {number(quantity['value'])}")
        cited.append(quantity)
    percent = share_value(share)
    parts.append(f"비중은 {number(percent)}%")
    cited.append(share)
    fact = f"{label['value']}의 {', '.join(parts)}입니다."
    return kind, float(percent), insight(
        str(label["value"]), fact, _refs(sheet, cited), "metric"
    )


def _same_scope(members, schema):
    used = {value for value in schema.values() if isinstance(value, int)}
    extra = set().union(*(set(row) for row, *_ in members)) - used
    return all(len({str(row[col].get("value", "")) for row, *_ in members if col in row}) <= 1
               for col in extra)


def _get(row, schema, role):
    return row.get(schema[role]) if role in schema else None


def _refs(sheet, cells):
    return [reference(sheet, cell["cell"]) for cell in cells]
