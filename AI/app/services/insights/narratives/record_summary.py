"""Totals and concentration from complete, uniquely keyed source records."""
import math
import re

from app.services.insights.display.record_labels import record_header
from app.services.insights.facts.series_scalars import displayed_value, unit
from app.services.insights.facts.table_inputs import narrative_regions
from app.services.insights.narratives.narrative_values import finite, insight, reference
from app.services.insights.narratives.table_schema import column
from app.services.insights.narratives.record_context import describe_records
from app.services.insights.narratives.record_units import linked_record_currency, record_value
from app.services.insights.narratives.record_summary_support import _words, _range
from app.services.insights.narratives.record_concentration import append_concentration


_KEY = re.compile(r"\b(?:id|identifier|policy|invoice|order|transaction|reference|record)\b|번호|식별자", re.I)
_ADDITIVE = re.compile(r"\b(?:total|amount|value|revenue|sales|quantity|qty|units|count)\b|금액|매출|수량|건수", re.I)
_NONADDITIVE = re.compile(r"\b(?:unit|per|average|avg|rate|ratio|percent|percentage|margin|price)\b|단가|평균|비율|비중|률", re.I)
_TOTAL = re.compile(r"\b(?:grand\s+total|sub\s*total|total)\b|합계|총계|소계", re.I)
_BASIS = re.compile(r"(?:(?:currency|unit|units|scale|scenario|version|basis)(?:\s+(?:code|name))?|통화(?:\s*코드)?|단위|배율|시나리오|버전|기준)", re.I)


def record_summary_report(context):
    for sheet in context.get("sheets", []):
        previous = []
        for region in narrative_regions(sheet.get("business_facts", {})):
            rows = region.get("rows", [])
            if not rows:
                previous = []
                continue
            candidates = rows[:1]
            if previous and _adjacent(previous[-1], rows[0]):
                candidates = [previous[-1], *candidates]
            for header in candidates:
                records = rows[1:] if header is rows[0] else rows
                result = _report(sheet, header, records, context)
                if result:
                    return result
            previous = rows
    return [], ""


def _adjacent(first, second):
    return bool(first and second and int(re.search(r"\d+$", second[0]["cell"])[0])
                == int(re.search(r"\d+$", first[0]["cell"])[0]) + 1)


def _report(sheet_data, header, rows, context):
    sheet = sheet_data.get("name", "")
    if len(rows) < 5 or not all(isinstance(c.get("value"), str) for c in header):
        return None
    headers = {column(c): c for c in header if c.get("value")}
    records = [{column(c): c for c in row} for row in rows]
    keys = [p for p, c in headers.items() if _KEY.search(_words(c["value"]))]
    keys = [p for p in keys if all(p in row and row[p].get("value") not in (None, "") for row in records)
            and len({str(row[p]["value"]) for row in records}) == len(records)]
    if not keys or any(_TOTAL.search(str(c.get("value", "")).strip()) for row in rows for c in row):
        return None
    basis_refs = []
    source_unit, source_currency = "", ""
    for p, c in headers.items():
        if not _BASIS.fullmatch(_words(c["value"]).strip()):
            continue
        basis_cells = [row.get(p, {}) for row in records]
        values = {str(c.get("value", "")).strip() for c in basis_cells}
        # A quantity column named Units is a measure, not a unit declaration.
        if all(finite(c.get("value")) for c in basis_cells) and str(c["value"]).casefold() == "units":
            continue
        if len(values) != 1 or not next(iter(values)):
            return None
        basis_refs += [reference(sheet, c["cell"]), _range(sheet, basis_cells)]
        if re.search(r"currency|통화", _words(c["value"]), re.I):
            source_currency = next(iter(values))
        elif re.search(r"^unit$|단위", _words(c["value"]), re.I):
            source_unit = " ".join(filter(None, [source_unit, next(iter(values))]))
    measures = []
    for p, header_cell in headers.items():
        name = str(header_cell["value"])
        words = _words(name)
        # TotalPrice is an extended amount; UnitPrice and plain Price are not additive.
        additive_price = bool(re.search(r"\btotal\s+price\b", words, re.I))
        if p in keys or not _ADDITIVE.search(words) or (_NONADDITIVE.search(words) and not additive_price):
            continue
        cells = [row.get(p, {}) for row in records]
        if not all(finite(c.get("value")) for c in cells):
            continue
        units = {unit(c) for c in cells}
        if len(units) != 1 or "%" in units:
            continue
        values = [displayed_value(c) for c in cells]
        declared = next(iter(units))
        inherited = source_unit
        monetary = bool(re.search(r"amount|value|revenue|sales|total\s+price|금액|매출", words, re.I))
        if source_currency and monetary:
            inherited = source_currency
        if inherited and declared and inherited.casefold() != declared.casefold():
            continue
        unit_refs = []
        if not declared and not inherited and monetary:
            inherited, unit_refs = linked_record_currency(context, sheet_data, header, records, cells)
        measures.append((not bool(re.search(r"total|amount|value|revenue|sales|금액|매출", words, re.I)),
                         p, name, cells, values, declared or inherited, unit_refs))
    if not measures:
        return None
    measures.sort(key=lambda value: value[:2])
    key = keys[0]
    key_ref = _range(sheet, [row[key] for row in records])
    description = describe_records(context, sheet_data, headers, records)
    labels = [record_header(measure[2], description.kind) for measure in measures[:2]]
    display_names = {measure[2]: (f"{label}({measure[2]})" if labels.count(label) > 1 else label)
                     for measure, label in zip(measures[:2], labels)}
    items = []
    totals = []
    for _, p, name, cells, values, units, unit_refs in measures[:2]:
        total = math.fsum(values)
        evidence = [reference(sheet, headers[p]["cell"]), key_ref, _range(sheet, cells),
                    *basis_refs, *description.evidence, *unit_refs]
        label = display_names[name]
        statement = f"{label} 합계는 {record_value(total, units)}"
        totals.append(statement)
        # Keep the context in the canonical fact as well as the overview: its
        # subject, dates and description citations must survive validation.
        fact = f"{description.lead(len(records))} {statement}입니다."
        title = f"{description.subject} {label} 합계".strip()
        items.append(insight(title, fact, evidence, "metric", topic=name))
    overview = f"{description.lead(len(records))} {', '.join(totals)}입니다."
    return append_concentration(sheet, rows, headers, records, keys, measures, key_ref, description,
                                display_names, basis_refs, items, overview)
