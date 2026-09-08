"""Column roles for record tables, decided by shape rather than by wording."""
import re
from collections import Counter

from app.services.insights.facts.fact_trends import date_value
from app.services.insights.narratives.narrative_values import finite
from app.services.insights.narratives.table_dates import column as col
from app.services.insights.narratives.table_dates import date_axis, is_date

MIN_RECORDS = 5
MIN_COVERAGE = 0.8
MAX_CATEGORIES = 12
MAX_CATEGORY_SHARE = 0.6
MAX_LABEL_LENGTH = 60
IDENTIFIER_NAME = re.compile(r"\b(?:id|oid|no|code|key|seq)\b|번호|코드|일련", re.I)
IDENTIFIER_DIGITS = 6


def header_index(rows):
    """The first row that names columns: a name is never a date or a number."""
    for index, row in enumerate(rows[:6]):
        if len(rows) - index - 1 >= MIN_RECORDS and header_like(row):
            return index
    return None


def header_like(row):
    """Region detection often leaves a header on its own, above its records."""
    filled = [cell for cell in row if cell.get("value") not in (None, "")]
    texts = [cell for cell in filled
             if isinstance(cell.get("value"), str) and cell["value"].strip()]
    if len(texts) < 2 or len(texts) != len(filled):
        return False
    return not any(finite(cell.get("value")) or is_date(cell.get("value"))
                   for cell in filled)


def measurable(header_row, records):
    """True when the table is a measurement table other narratives already read."""
    if date_axis([header_row], 0, header_row):
        return True
    header = _named_columns(header_row)
    numeric = [position for position, name in header.items()
               if _numeric_column(position, records) and not _identifier(position, name, records)]
    return len(numeric) >= 2


def category_column(header, records):
    best = None
    for position, name in _named_columns(header).items():
        cells = _column_cells(position, records)
        if len(cells) < len(records) * MIN_COVERAGE or len(cells) < MIN_RECORDS:
            continue
        values = [str(cell["value"]).strip() for cell in cells]
        if not all(isinstance(cell["value"], str) for cell in cells):
            continue
        if any(len(value) > MAX_LABEL_LENGTH or not value for value in values):
            continue
        counts = Counter(values)
        if not 2 <= len(counts) <= MAX_CATEGORIES:
            continue
        if len(counts) > len(values) * MAX_CATEGORY_SHARE:
            continue
        candidate = (len(counts), -len(cells), position, name, counts, cells)
        if best is None or candidate[:3] < best[:3]:
            best = candidate
    if best is None:
        return None
    _, _, _, name, counts, cells = best
    return name, counts.most_common(), cells


def date_column(header, records):
    for position, name in _named_columns(header).items():
        cells = _column_cells(position, records)
        dated = [cell for cell in cells if is_date(cell.get("value"))]
        if len(dated) < len(records) * MIN_COVERAGE or len(dated) < MIN_RECORDS:
            continue
        keys = [_key(cell["value"]) for cell in dated]
        ordered = sorted(keys)
        return name, [ordered[0], ordered[-1]], Counter(keys).most_common(), dated
    return None


def _named_columns(header):
    return {
        col(cell): " ".join(str(cell["value"]).split())
        for cell in header
        if isinstance(cell.get("value"), str) and cell["value"].strip()
    }


def _column_cells(position, records):
    found = []
    for record in records:
        cell = next((item for item in record if col(item) == position), None)
        if cell is not None and cell.get("value") not in (None, ""):
            found.append(cell)
    return found


def _numeric_column(position, records):
    cells = _column_cells(position, records)
    return bool(cells) and all(finite(cell["value"]) for cell in cells)


def _identifier(position, name, records):
    """Row keys look like measures but never carry a quantity worth comparing."""
    if IDENTIFIER_NAME.search(name):
        return True
    cells = _column_cells(position, records)
    values = [cell["value"] for cell in cells if finite(cell["value"])]
    if len(values) < MIN_RECORDS or len(set(values)) < len(values):
        return False
    return all(
        float(value).is_integer() and len(str(abs(int(value)))) >= IDENTIFIER_DIGITS
        for value in values
    )


def _key(value):
    parsed = date_value(value)
    return parsed.isoformat() if parsed else " ".join(str(value).split())
