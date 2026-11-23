"""Small tables of named items over a few numeric columns, read by what their columns are.

- Columns that are periods (FY2021 … FY2024, 1월 · 2월): each item's change over them.
- A plan beside its actual (계획 · 실적, 예산 · 실적, 기준값 · 측정값): how the actual stands to the plan.
- Other columns: the item each column is largest and smallest for.
"""
import re

from app.services.insights.facts.sheet_scope import narrative_sheet_groups
from app.services.insights.facts.table_inputs import narrative_regions
from app.services.insights.narratives.item_likert import likert_items
from app.services.insights.narratives.item_pairs import pair_items
from app.services.insights.narratives.item_periods import period_items
from app.services.insights.narratives.layout_tables import (
    NONADDITIVE, TOTAL, UNIT, _place, amount, heading, label, noted, numbers, sheet_tables, span,
)
from app.services.insights.narratives.narrative_values import finite, insight, subject_particle, topic_particle

_UNIT_LINE = re.compile(r"단위\s*[:：]\s*([^\s/,;)]+)|\(([A-Za-z$€£]+\s+(?:thousands|millions|billions))\)", re.I)
_SOURCE = re.compile(r"^\s*(?:출처|자료\s*출처|source)\s*[:：]\s*([^/]+)", re.I)
_TITLED = re.compile(r"\S별(?:\s|$)|현황|추이|통계|내역|분석|자료|보고서|실적|명부|목록|일지|대장|\b(?:report|summary|by)\b",
                    re.I)  # a table's title names what it is: 월별 매출, 점검 현황, Monthly Yield Report
FEW = 8  # more rows are records, read by their mean elsewhere


def item_table_report(context):
    primary, comparisons = narrative_sheet_groups(context)
    for _, sheet in primary or comparisons:
        for table in item_tables(sheet):
            key = min(table["header"][-1] | table["header"][0])
            rows = [row for row in table["rows"] if _name(row, key)  # 'Net sales:' over its lines holds no value
                    and any(finite(cell.get("value")) for p, cell in row.items() if p != key)]
            measures = [p for p in sorted(set().union(*table["header"])) if p != key and numbers(rows, p)]
            if len(rows) < 3 or not measures:  # two items are read off the table itself
                continue
            for reader in (period_items, pair_items, likert_items, _ranked):
                items = reader(table, key, rows, measures)
                if items:
                    return items, _overview(sheet, table, items, reader is period_items)
    return [], ""


def _overview(sheet, table, items, series):
    """The table's own title as the first sentence (출처 when the sheet names one), then its findings."""
    from app.services.insights.narratives.source_overview import compact_facts
    body = compact_facts(items) if series else " ".join(item.fact for item in items[:2])
    title = " ".join(UNIT.sub("", table["title"]).split()).strip(" .")
    if not title:
        return body
    source = next((found[1].strip() for region in narrative_regions(sheet.get("business_facts", {}))
                   for row in region.get("rows", []) for cell in row
                   if (found := _SOURCE.match(str(cell.get("value") or "")))), "")
    lead = f"이 파일에는 {title} 자료가 담겨 있습니다." + (f" (출처: {source})" if source else "")
    return f"{lead}\n{body}" if series else f"{lead} {body}"


def item_tables(sheet):
    """Header-and-data tables, a single region whose first row names its columns, and a total row under either."""
    regions = [region for region in narrative_regions(sheet.get("business_facts", {}))
               if region.get("start_cell") and region.get("end_cell") and region.get("rows")]
    tables = sheet_tables(sheet)
    for region in regions:
        rows = region["rows"]
        if region.get("role") in {"header", "title", "unit", "description", "total"} or len(rows) < 3:
            continue
        if all(isinstance(cell.get("value"), str) for cell in rows[0]) and len(rows[0]) >= 3 and any(
                not isinstance(cell.get("value"), str) for cell in rows[1]):
            tables.append({"sheet": str(sheet.get("name", "")), "title": "", "unit": "", "title_cell": None,
                           "header": [{_place(cell["cell"])[0]: cell for cell in rows[0]}],
                           "rows": [{_place(cell["cell"])[0]: cell for cell in row} for row in rows[1:]]})
    for table in tables:
        last = max(_place(cell["cell"])[1] for row in table["rows"] for cell in row.values())
        total = next((region for region in regions if region.get("role") == "total"
                      and _place(region["start_cell"])[1] == last + 1), None)
        table["total"] = {_place(cell["cell"])[0]: cell for cell in total["rows"][0]} if total else None
        table["unit"] = table["unit"] or _unit(regions, table)
        table["title"] = _title(regions, table)
    return tables


def _title(regions, table):
    """The one-cell line nearest above the table in its first column, not a unit line: '2026년 상반기 월별 매출'."""
    left = min(table["header"][0])
    top = min(_place(cell["cell"])[1] for cell in table["header"][0].values())
    above = [region["rows"][0][0] for region in regions if region.get("role") in {"title", "description", "unit"}
             and len(region["rows"]) == 1 and len(region["rows"][0]) == 1
             and _place(region["start_cell"])[0] == left and _place(region["end_cell"])[1] < top]
    texts = [" ".join(UNIT.sub("", str(cell.get("value") or "")).split()) for cell in above]  # '(단위: 만원)' aside
    texts = [text for text in texts if text and not _UNIT_LINE.search(text) and not _SOURCE.match(text)]
    return texts[-1] if texts and _TITLED.search(texts[-1]) else ""  # 'Income (net, after tax)' is a label


def _unit(regions, table):
    top = min(_place(cell["cell"])[1] for row in table["header"] for cell in row.values())
    texts = [str(cell.get("value")) for region in regions for row in region["rows"] for cell in row
             if _place(cell["cell"])[1] <= top and isinstance(cell.get("value"), str)]
    for text in texts:
        if found := _UNIT_LINE.search(text):
            return (found[1] or found[2]).strip()
        if (found := UNIT.fullmatch(text.strip())) and not re.search(r"\d{4}", found[1]):
            return found[1].strip()
    return ""


def _name(row, key):
    value = row.get(key, {}).get("value")
    return isinstance(value, str) and value.strip() and not TOTAL.search(value.strip())


def _ranked(table, key, rows, measures):
    """The largest and smallest item of each column ('합계' alone when the table has one)."""
    if len(rows) >= FEW:
        return []
    totals = [p for p in measures if TOTAL.search(label(table, p))]
    names = {id(row): row[key]["value"].strip() for row in rows}
    items = []
    for p in (totals or measures)[:3]:
        values = numbers(rows, p)
        what = label(table, p)
        ordered = sorted(zip(values, rows), key=lambda pair: -pair[0])
        (top, first), (bottom, last) = ordered[0], ordered[-1]
        said = f"{names[id(first)]}({amount(top)})"
        least = f"{names[id(last)]}({amount(bottom)})"
        high, low = ("높고", "낮습니다") if NONADDITIVE.search(what) else ("많고", "적습니다")
        fact = (f"‘{what}’{topic_particle(what)} {said}{subject_particle(said)} 가장 {high}, "
                f"{least}{subject_particle(least)} 가장 {low}.")
        items.append(insight(f"{label(table, key)}별 {what}", noted(fact, table["unit"]),
                             [heading(table, p), span(table, rows, p), span(table, rows, key)], "metric", topic=what))
    return items
