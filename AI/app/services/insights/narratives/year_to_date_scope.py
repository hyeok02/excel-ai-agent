"""Prove a calendar YTD window from the same metric's monthly source cells."""
import calendar
import math
import re

from app.services.insights.facts.series_scalars import displayed_value, unit
from app.services.insights.narratives.narrative_values import finite, reference
from app.services.insights.narratives.table_schema import column

_YTD = re.compile(r"^(?:year[\s-]+to[\s-]+date|ytd|연초\s*(?:이후|부터)\s*누적|연간\s*누계)$", re.I)
_YEAR = re.compile(r"^(?:year\s*)?((?:19|20|21)\d{2})(?:\s*년)?$", re.I)
_MONTHS = {name.casefold(): month for month in range(1, 13)
           for name in (calendar.month_name[month], calendar.month_abbr[month])}
_MONTHS["sept"] = 9
_NON_ADDITIVE = re.compile(r"\b(?:average|mean|price|rate|ratio|percent(?:age)?|margin)\b|평균|단가|비율|증감률|증가율|비중", re.I)


def year_to_date_scope(sheet, section, metric_column, records, *, series):
    """Return a proved ``(label, references)`` or ``('', [])``.

    ``series`` is the caller's parsed vertical series list. Matching the original
    header cells keeps a same-named metric in a second table out of this proof.
    No latest date, sheet name, filename, or publisher supplies a month implicitly.
    """
    if not _YTD.fullmatch(str(section).strip()) or len(records) < 2:
        return "", []
    signature = _signature(records, metric_column)
    targets = [entry for entry in series
               if entry[1] == section and _signature(entry[3], metric_column) == signature]
    if len(targets) != 1:
        return "", []
    header, _, section_cell, _, unit_note = targets[0]
    if not section_cell:
        return "", []
    metric = next((cell for cell in header[1:] if column(cell) == metric_column), None)
    if not metric or _NON_ADDITIVE.search(str(metric.get("value", ""))):
        return "", []
    target_by_year = {}
    for date, axis, values in records:
        year = _axis_year(axis.get("value"))
        value = values.get(metric_column, {})
        if (year != date.year or date.year in target_by_year
                or not finite(value.get("value")) or unit(value) == "%"):
            return "", []
        target_by_year[date.year] = axis, value
    header_key = _header_key(header, metric_column)
    monthly = {}
    for candidate_header, candidate_section, year_cell, monthly_records, candidate_unit in series:
        year = _YEAR.fullmatch(str(candidate_section).strip())
        if (not year or int(year[1]) not in target_by_year or not year_cell
                or _header_key(candidate_header, metric_column) != header_key
                or _unit_key(candidate_unit) != _unit_key(unit_note)
                or _row(year_cell) >= _row(section_cell)):
            continue
        year = int(year[1])
        if year in monthly:
            return "", []  # Two possible source blocks must not be chosen arbitrarily.
        months = {}
        for date, axis, values in monthly_records:
            month = _month(axis.get("value"), year)
            if (not month or date.year != year or date.month != month
                    or month in months or _row(axis) >= _row(section_cell)):
                return "", []
            months[month] = axis, values.get(metric_column, {})
        if not months or sorted(months) != list(range(1, max(months) + 1)):
            return "", []
        monthly[year] = year_cell, months
    if set(monthly) != set(target_by_year):
        return "", []
    common_endpoints = set(range(1, 13))
    for year, (_, target) in target_by_year.items():
        running, matches = [], set()
        for month in range(1, 13):
            pair = monthly[year][1].get(month)
            if not pair or not finite(pair[1].get("value")) or unit(pair[1]) != unit(target):
                break
            running.append(displayed_value(pair[1]))
            if math.isclose(math.fsum(running), displayed_value(target), rel_tol=1e-10, abs_tol=1e-7):
                matches.add(month)
        common_endpoints.intersection_update(matches)
    if len(common_endpoints) != 1:
        return "", []
    endpoint = common_endpoints.pop()
    cells = [header[0], metric, section_cell]
    if unit_note:
        cells.append(unit_note)
    for year in sorted(target_by_year):
        cells.extend(target_by_year[year])
        year_cell, months = monthly[year]
        cells.append(year_cell)
        for month in range(1, endpoint + 1):
            cells.extend(months[month])
    refs = list(dict.fromkeys(reference(sheet.get("name", ""), cell["cell"]) for cell in cells))
    return f"(1~{endpoint}월 누적)", refs


def _signature(records, position):
    return tuple(sorted((record[0], record[1].get("cell"), record[2].get(position, {}).get("cell"))
                        for record in records))


def _header_key(header, position):
    metric = next((cell for cell in header if column(cell) == position), {})
    parent = metric.get("_parent") or {}
    return (header[0].get("cell"), metric.get("cell"), metric.get("value"),
            parent.get("cell"), parent.get("value"))


def _unit_key(note):
    return (note.get("cell"), note.get("value")) if note else None


def _row(cell):
    match = re.search(r"\d+$", str(cell.get("cell", "")))
    return int(match[0]) if match else -1


def _axis_year(value):
    if finite(value) and float(value).is_integer() and 1900 <= value <= 2200:
        return int(value)
    match = _YEAR.fullmatch(str(value).strip())
    return int(match[1]) if match else None


def _month(value, year):
    text = str(value).strip().casefold().rstrip(".")
    if text in _MONTHS:
        return _MONTHS[text]
    korean = re.fullmatch(r"(?:(\d{4})년\s*)?(1[0-2]|[1-9])월", text)
    if korean and (not korean[1] or int(korean[1]) == year):
        return int(korean[2])
    explicit = re.fullmatch(r"(\d{4})[-/.](0?[1-9]|1[0-2])", text)
    if explicit and int(explicit[1]) == year:
        return int(explicit[2])
    return None
