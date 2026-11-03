"""Read complete vertical source sections and their date axes."""
import calendar
import re
from datetime import datetime

from app.services.insights.facts.fact_trends import date_value
from app.services.insights.facts.horizontal_context import declared_axis_unit
from app.services.insights.facts.table_inputs import narrative_regions
from app.services.insights.narratives.narrative_values import finite
from app.services.insights.narratives.table_schema import column


_AXIS = re.compile(r"^(?:date|month|year|period|quarter|일자|날짜|연도|년도|월|기간|분기)$", re.I)
_MONTHS = {name.casefold(): i for i in range(1, 13) for name in (calendar.month_name[i], calendar.month_abbr[i])}
_MONTHS["sept"] = 9


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
