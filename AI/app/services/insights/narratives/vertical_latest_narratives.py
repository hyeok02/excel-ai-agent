"""Recent changes on explicit vertical date axes, preserving period sections."""
import calendar
import re
from datetime import datetime

from app.services.insights.display.source_labels import narrative_scope, section_label, source_label, source_unit
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.facts.horizontal_context import declared_axis_unit
from app.services.insights.facts.series_scalars import displayed_value, unit
from app.services.insights.facts.sheet_scope import comparison_sheet
from app.services.insights.facts.table_inputs import narrative_regions
from app.services.insights.narratives.narrative_values import direction_particle, finite, insight, number, overall, period, reference, topic_particle
from app.services.insights.narratives.table_schema import column
from app.services.insights.narratives.series_path import path_direction
from app.services.insights.narratives.year_to_date_scope import year_to_date_scope

_AXIS = re.compile(r"^(?:date|month|year|period|quarter|일자|날짜|연도|년도|월|기간|분기)$", re.I)
_MONTHS = {name.casefold(): i for i in range(1, 13) for name in (calendar.month_name[i], calendar.month_abbr[i])}
_MONTHS["sept"] = 9


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


def _series(sheet):
    header, section, section_cell, records, source_rows, unit_note = None, "", None, [], {}, None
    for region in narrative_regions(sheet.get("business_facts", {})):
        rows = region.get("rows", [])
        if not rows:
            if header and len(records) >= 2:
                yield header, section, section_cell, records, unit_note
            header, records, section, section_cell = None, [], "", None
            continue
        for row in rows:
            populated = sorted((c for c in row if c.get("value") not in (None, "")), key=column)
            if not populated:
                continue
            first = populated[0]
            row_number = int(re.search(r"\d+$", first["cell"])[0])
            source_rows[row_number] = {column(c): c for c in populated}
            if _AXIS.fullmatch(str(first["value"]).strip()) and len(populated) >= 2:
                if header and len(records) >= 2:
                    yield header, section, section_cell, records, unit_note
                header = _qualified_header(populated, source_rows.get(row_number - 1, {}))
                records, section, section_cell = [], "", None
                unit_note = declared_axis_unit(source_rows, row_number)
                preceding = list(source_rows.get(row_number - 1, {}).values())
                if len(preceding) == 1 and (not unit_note or preceding[0]["cell"] != unit_note["cell"]):
                    title = str(preceding[0].get("value", "")).strip()
                    if title and len(title) <= 160:
                        section, section_cell = title, preceding[0]
                continue
            if header:
                axis = next((c for c in populated if column(c) == column(header[0])), None)
                date = _date(axis.get("value"), section) if axis else None
                if date:
                    records.append((date, axis, {column(c): c for c in populated}))
                    continue
                if len(records) >= 2:
                    yield header, section, section_cell, records, unit_note
                records = []
                if len(populated) == 1 and column(first) == column(header[0]):
                    section, section_cell = str(first["value"]).strip(), first
                else:
                    header, section, section_cell = None, "", None
    if header and len(records) >= 2:
        yield header, section, section_cell, records, unit_note


def _date(value, section):
    if finite(value) and float(value).is_integer() and 1900 <= value <= 2200:
        return datetime(int(value), 1, 1)
    text = str(value).strip()
    if re.fullmatch(r"(?:19|20|21)\d{2}", text):
        return datetime(int(text), 1, 1)
    parsed = date_value(value)
    if parsed:
        return parsed
    year = re.fullmatch(r"(?:year\s*)?((?:19|20|21)\d{2})", section, re.I)
    if year and text.casefold().rstrip(".") in _MONTHS:
        return datetime(int(year[1]), _MONTHS[text.casefold().rstrip(".")], 1)
    return None


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
        metric_display = source_label(metric, f"{sheet.get('name', '')} {section}")
        scope += "".join(f" · {source_label(label)}: {value}" for label, value, _ in dimensions)
        subject = f"{scope}의 {metric_display}" if scope else metric_display
        latest_amount = f"{number(right)}{_suffix(units)}"
        fact = (f"{subject}{topic_particle(metric_display)} {_period(previous)} {number(left)}{_suffix(units)}에서 "
                f"{_period(latest)} {latest_amount}{direction_particle(latest_amount)} ")
        delta = right - left
        if delta == 0:
            fact += "변동이 없습니다."
        else:
            fact += f"{number(abs(delta))}{'%p' if units == '%' else _suffix(units)} {'증가' if delta > 0 else '감소'}했습니다."
            if units != "%" and left > 0:
                fact += f" 이전 기간 대비 {number(abs(delta / left * 100))}% {'증가' if delta > 0 else '감소'}했습니다."
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
        path, path_refs = _path(sheet.get("name", ""), records, position, units)
        fact += path
        evidence.extend(path_refs)
        priority = (0, position) if overall(metric) and not re.search(r"estimated|추정", metric, re.I) else (1 if units == "%" else 2, len(metric), position)
        title_section = section_label(section)
        if window:
            title_section = f"{title_section} {window}".strip()
        title = f"{metric_display} 최근 변화" + (f" · {title_section}" if title_section and len(title_section) <= 40 else "")
        options.append((priority, units, insight(title, fact, evidence, "change", topic=metric)))
    ordered = sorted(options, key=lambda option: option[0])
    if any(option[1] != "%" for option in ordered):
        rates = [option for option in ordered if option[1] == "%"]
        ordered = sorted([option for option in ordered if option[1] != "%"] + rates[:1], key=lambda option: option[0])
    return [item for _, _, item in ordered[:3]]


def _period(record):
    original = record[1]["value"]
    if finite(original) or re.fullmatch(r"(?:19|20|21)\d{2}", str(original).strip()):
        return f"{record[0].year}년"
    if str(original).casefold().rstrip(".") in _MONTHS:
        return f"{record[0].year}년 {record[0].month}월"
    return period(original)


def _suffix(units):
    return f" {units}" if units else ""


def _basis_priority(section):
    if re.search(r"annual|calendar|연간", section, re.I):
        return 0
    if re.search(r"year\s+to\s+date|\bytd\b|누적", section, re.I):
        return 1
    if re.search(r"rolling|trailing|이동", section, re.I):
        return 3
    return 2


def _qualified_header(header, preceding):
    # A separate group-header row bounds each parent up to the next parent.
    # Keeping this label prevents bare '7 days' or 'Total' from losing its basis.
    if (len(preceding) < 2 or min(preceding) <= column(header[0])
            or not all(isinstance(c.get("value"), str) for c in preceding.values())):
        return header
    result = []
    for cell in header:
        parents = [p for p in preceding if p <= column(cell)]
        parent = preceding[max(parents)] if parents else None
        result.append({**cell, "_parent": parent} if parent else cell)
    return result


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


def _path(sheet, records, position, units):
    if not 3 <= len(records) <= 12:
        return "", []
    cells = [record[2].get(position, {}) for record in records]
    if not all(finite(c.get("value")) for c in cells) or len({unit(c) for c in cells}) != 1:
        return "", []
    values = [displayed_value(c) for c in cells]
    indexes = sorted({0, len(records) // 3, 2 * len(records) // 3, len(records) - 1})
    timeline = " → ".join(f"{_period(records[i])} {number(values[i])}{_suffix(units)}" for i in indexes)
    coverage = "기간별 기록" if len(indexes) == len(records) else "주요 시점의 기록"
    text = f" {coverage}은 {timeline}입니다. {path_direction(values)}"
    evidence = []
    for source in ([record[1] for record in records], cells):
        ordered = sorted(source, key=lambda c: int(re.search(r"\d+$", c["cell"])[0]))
        evidence.append(reference(sheet, f"{ordered[0]['cell']}:{ordered[-1]['cell']}"))
    return text, evidence
