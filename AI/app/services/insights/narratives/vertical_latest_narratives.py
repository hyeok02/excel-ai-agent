"""Recent changes on explicit vertical date axes, preserving period sections."""
import re

from app.services.insights.facts.sheet_scope import comparison_sheet
from app.services.insights.narratives.vertical_latest_series import _AXIS, _MONTHS, _series, _date, _qualified_header
from app.services.insights.narratives.vertical_latest_format import _period, _suffix, _path
from app.services.insights.narratives.vertical_latest_items import _items, _dimensions


def vertical_latest_report(context):
    candidates = []
    sheets = list(enumerate(context.get("sheets", [])))
    sheets.sort(key=lambda pair: (comparison_sheet(pair[1]),
                                 not bool(re.search(r"\b(?:all|overall|total)\b|전체", str(pair[1].get("name", "")), re.I)), pair[0]))
    for sheet_order, (_, sheet) in enumerate(sheets):
        series = list(_series(sheet))
        for header, section, section_cell, records, unit_note in series:
            for metric_order, item in enumerate(_items(sheet, header, section, section_cell, records, unit_note, series)):
                candidates.append((sheet_order, section, max(record[0] for record in records), metric_order, item))
    if not candidates:
        return [], ""
    first_sheet = min(candidate[0] for candidate in candidates)
    grouped = {}
    for candidate in candidates:
        if candidate[0] != first_sheet:
            continue
        basis = re.sub(r"\b(?:year\s*)?\d{4}\b", "", candidate[1], flags=re.I).strip()
        current = grouped.get(basis)
        if current is None or candidate[2] > current[0]:
            grouped[basis] = candidate[2], [candidate]
        elif candidate[2] == current[0]:
            current[1].append(candidate)
    ordered = sorted(grouped.values(), key=lambda item: (_basis_priority(item[1][0][1]), -item[0].timestamp()))
    items = [min(group[1], key=lambda c: c[3])[4] for group in ordered[:3]]
    if len(items) < 3 and ordered:
        for candidate in sorted(ordered[0][1], key=lambda c: c[3]):
            if candidate[4] not in items:
                items.append(candidate[4])
            if len(items) == 3:
                break
    return items, " ".join(item.fact for item in items)


def _basis_priority(section):
    if re.search(r"annual|calendar|연간", section, re.I):
        return 0
    if re.search(r"year\s+to\s+date|\bytd\b|누적", section, re.I):
        return 1
    if re.search(r"rolling|trailing|이동", section, re.I):
        return 3
    return 2
