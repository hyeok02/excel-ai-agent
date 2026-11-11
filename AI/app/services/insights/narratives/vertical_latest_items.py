"""Compute recent metric changes within one source section and identity."""
import re

from app.services.insights.display.source_labels import narrative_scope, section_label, source_label, source_unit
from app.services.insights.facts.series_scalars import displayed_value, unit
from app.services.insights.narratives.category_share_subject import category_share_subject
from app.services.insights.narratives.change_sentence import change_fact, change_sentence
from app.services.insights.narratives.narrative_values import finite, insight, number, overall, reference
from app.services.insights.narratives.table_schema import column
from app.services.insights.narratives.year_to_date_scope import year_to_date_scope
from app.services.insights.narratives.vertical_latest_format import _period, _suffix, _path


def _items(sheet, header, section, section_cell, records, unit_note, series):
    if len({row[0] for row in records}) != len(records):
        return []
    records = sorted(records, key=lambda record: record[0])
    dimensions = _dimensions(header, records)
    if dimensions is None:
        return []
    previous, latest = records[-2:]
    options = []
    for cell in header[1:]:
        position = column(cell)
        metric = " ".join(str(cell.get("value", "")).split())
        parent = cell.get("_parent")
        if parent and " ".join(str(parent["value"]).split()).casefold() not in metric.casefold():
            metric = f"{' '.join(str(parent['value']).split())} · {metric}"
        if not metric or metric.startswith("#"):
            continue
        pair = [row[2].get(position, {}) for row in (previous, latest)]
        if not all(finite(c.get("value")) for c in pair) or len({unit(c) for c in pair}) != 1:
            continue
        left, right = (displayed_value(c) for c in pair)
        units = unit(pair[0])
        declared_currency = next((value for label, value, _ in dimensions
                                  if re.fullmatch(r"currency(?:\s+code)?|통화(?:\s*코드)?", label, re.I)), "")
        if declared_currency and units not in ("", "%") and units.casefold() != declared_currency.casefold():
            continue
        if declared_currency and not units and re.search(r"revenue|sales|amount|value|price|매출|금액", metric, re.I):
            units = declared_currency
        applied_unit_note = unit_note if not units else None
        if applied_unit_note:
            units = source_unit(applied_unit_note["value"])
        scope = narrative_scope(sheet.get("name", ""), section)
        window, window_refs = year_to_date_scope(sheet, section, position, records, series=series)
        if window:
            scope = f"{scope} {window}".strip()
        share = category_share_subject(section, metric, [item.get("value") for item in header[1:]])
        metric_display = source_label(metric, f"{sheet.get('name', '')} {section}")
        scope += "".join(f" · {source_label(label)}: {value}" for label, value, _ in dimensions)
        subject = share[1] if share and not dimensions and not window else (
            f"{scope}의 {metric_display}" if scope else metric_display)
        # Same shape as a series laid out across columns: whole period, latest step, path.
        recent = change_sentence(f"{_period(previous)} {number(left)}{_suffix(units)}",
                                 f"{_period(latest)} {number(right)}{_suffix(units)}", left, right, _suffix(units))
        whole, shape, path_refs = _path(sheet.get("name", ""), records, position, units)
        label = share[0] if share and subject == share[1] else subject
        fact = change_fact(label, whole, recent, shape) if whole else change_fact(label, recent)
        evidence = [reference(sheet.get("name", ""), c["cell"]) for c in [cell, previous[1], latest[1], *pair]]
        evidence.extend(window_refs)
        if section_cell:
            evidence.append(reference(sheet.get("name", ""), section_cell["cell"]))
        if parent:
            evidence.append(reference(sheet.get("name", ""), parent["cell"]))
        if applied_unit_note:
            evidence.append(reference(sheet.get("name", ""), applied_unit_note["cell"]))
        for _, _, dimension_cells in dimensions:
            evidence.extend(reference(sheet.get("name", ""), c["cell"]) for c in dimension_cells)
        evidence.extend(path_refs)
        priority = (0, position) if overall(metric) and not re.search(r"estimated|추정", metric, re.I) else (1 if units == "%" else 2, len(metric), position)
        title_section = share[2] if share else section_label(section)
        if window:
            title_section = f"{title_section} {window}".strip()
        title_metric = share[0] if share else metric_display
        title = f"{title_metric} 변화" + (f" · {title_section}" if title_section and len(title_section) <= 40 else "")
        options.append((priority, units, insight(title, fact, evidence, "change", topic=metric)))
    ordered = sorted(options, key=lambda option: option[0])
    if any(option[1] != "%" for option in ordered):
        rates = [option for option in ordered if option[1] == "%"]
        ordered = sorted([option for option in ordered if option[1] != "%"] + rates[:1], key=lambda option: option[0])
    return [item for _, _, item in ordered[:3]]


def _dimensions(header, records):
    dimensions = []
    for header_cell in header[1:]:
        cells = [record[2].get(column(header_cell), {}) for record in records]
        labels = [c.get("value") for c in cells]
        texts = [v for v in labels if isinstance(v, str) and v and not v.startswith("#")]
        if not texts:
            continue
        # A repeated company, scenario, currency or other categorical column
        # is part of the series identity; different identities never form a trend.
        if len(texts) >= len(records) * .8:
            if len(texts) != len(records) or len(set(texts)) != 1:
                return None
            dimensions.append((str(header_cell["value"]), texts[0], [header_cell, *cells]))
    return dimensions
