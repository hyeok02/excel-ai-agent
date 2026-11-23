"""Record lists whose values are not to be added up, read from the table itself.

- Years written as the columns ('1990', '1991', …): each row is a series of years, not one record.
- An average said above the table ('Timeseries of the average number of beds'): levels, not flows.
- Rows of several levels (나라 · 지역 · 시군구): one level's rows add up to another row of the table.
"""
import re

from app.services.insights.facts.table_inputs import narrative_regions
from app.services.insights.narratives.narrative_values import finite
from app.services.insights.narratives.table_schema import column

_YEAR = re.compile(r"^(?:19|20)\d{2}$")
_AVERAGE = re.compile(r"\b(?:average|mean)\b|평균", re.I)


def not_summable(sheet, header, records):
    if sum(bool(_YEAR.match(str(cell.get("value", "")).strip())) for cell in header) >= 2:
        return True
    return _averaged(sheet, header) or _nested(header, records)


def _row(cell):
    return int(re.search(r"\d+$", cell["cell"])[0])


def _averaged(sheet, header):
    top = _row(header[0])
    return any(isinstance(cell.get("value"), str) and _AVERAGE.search(cell["value"]) and _row(cell) < top
               for region in narrative_regions(sheet.get("business_facts", {}))
               for row in region.get("rows", []) for cell in row)


def _nested(header, records):
    """Rows of several levels: one row totalling the others ('England and Wales' over its districts),
    or one level's rows adding up to another row (the 9 regions to England)."""
    positions = [column(cell) for cell in header]
    measures = [p for p in positions if all(finite(row.get(p, {}).get("value")) for row in records)]
    if not measures:
        return False
    values = [row[measures[0]]["value"] for row in records]
    total = sum(values)
    if len(values) >= 3 and any(value > 0 and abs(value - (total - value)) <= value * 0.005 for value in values):
        return True
    levels = [p for p in positions if 2 <= len({str(row.get(p, {}).get("value")) for row in records}) <= 30
              and all(isinstance(row.get(p, {}).get("value"), str) for row in records)]
    for level in levels:
        groups = {}
        for row in records:
            groups.setdefault(row[level]["value"], []).append(row[measures[0]]["value"])
        for parts in groups.values():
            whole = sum(parts)
            if len(parts) >= 3 and whole > 0 and any(
                    abs(value - whole) <= whole * 0.001 and value >= 3 * max(parts) for value in values):
                return True
    return False
