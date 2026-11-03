"""Explicit period and measurement context for a horizontal source table."""
from datetime import datetime
import re

from app.services.insights.facts.fact_trends import date_value

_YEAR = re.compile(r"(?:(mid)[-\s])?((?:19|20|21)\d{2})(년)?", re.I)
_YEAR_LABEL = re.compile(r"^(?:year|years|calendar year|연도|년도|연간)$", re.I)
_UNIT = re.compile(
    r"(?:percent(?:age)?|%|(?:[A-Z]{3}|cents?|pence|dollars?|euros?|원|달러)\s+per\s+[A-Za-z]+"
    r"|(?:thousand|million|billion)\s+(?:tonnes?|tons?|megawatthours?|kilowatthours?|persons?|people)"
    r"(?:\s+carbon dioxide equivalent)?|(?:kg|kwh|mwh|gwh|twh|tonnes?|tons?|명|천명|백만명))",
    re.I,
)


def axis_dates(row, cells, rows):
    """Standalone years are dates only when the table supplies period context.

    In particular, a row of four-digit quantities/identifiers alone is not a
    year axis. Explicit 'Mid-2024'/'2024년' labels or a year heading/title span
    supply the extra evidence, without changing the general cell date parser.
    """
    years = {column: _year(cell.get("value")) for column, cell in cells.items()}
    years = {column: value for column, value in years.items() if value}
    context = [str(cell.get("value", "")) for number in range(max(1, row - 10), row)
               for values in [rows.get(number, {})] if len(values) <= 2
               for cell in values.values()]
    year_labels = any(_YEAR_LABEL.fullmatch(str(cell.get("value", "")).strip())
                      for cell in cells.values())
    endpoints = {str(value[0]) for value in years.values()}
    contextual_years = len(years) >= 2 and (year_labels or any(
        len(endpoints & set(re.findall(r"(?<!\d)(?:19|20|21)\d{2}(?!\d)", text))) >= 2
        for text in context
    ))
    result = {}
    for column, cell in cells.items():
        parsed = date_value(cell.get("value"))
        annual = years.get(column)
        if parsed:
            result[column] = parsed
        elif annual and (contextual_years or annual[1]):
            result[column] = datetime(annual[0], 7 if annual[2] else 1, 1)
    return result


def period_label(value):
    annual = _year(value)
    if annual:
        return f"{annual[0]}년{' 중간' if annual[2] else ''}"
    from app.services.insights.narratives.narrative_values import period
    return period(value)


def declared_axis_unit(rows, start):
    """Keep an explicit nearby table unit and its source cell, never guess it."""
    candidates = []
    for row in range(max(1, start - 10), start):
        cells = rows.get(row, {})
        if len(cells) != 1:
            continue
        cell = next(iter(cells.values()))
        text = str(cell.get("value", ""))
        fragments = re.findall(r"\(([^()]+)\)", text)
        fragments += re.findall(r"\bin\s+([^,;()]+)", text, re.I)
        fragments += re.findall(r"(?:unit(?:s)?|단위)\s*[:：]\s*([^,;()]+)", text, re.I)
        for fragment in fragments:
            fragment = fragment.strip()
            if _UNIT.fullmatch(fragment):
                candidates.append({"value": fragment, "cell": cell["cell"]})
    distinct = {candidate["value"].casefold() for candidate in candidates}
    return candidates[-1] if len(distinct) == 1 else None


def _year(value):
    if isinstance(value, bool):
        return None
    text = str(value).strip()
    match = _YEAR.fullmatch(text)
    if not match:
        return None
    return int(match[2]), bool(match[1] or match[3]), bool(match[1])
