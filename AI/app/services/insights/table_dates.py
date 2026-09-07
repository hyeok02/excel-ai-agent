"""Date-axis recognition that rejects duplicate periods and reporting bases."""
import re

from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

from app.services.insights.fact_trends import date_value

BASIS_HEADER = re.compile(
    r"\b(?:mrq|mry|ltm|ttm|ytd|qtd|fy|fiscal\s+year|quarter)\b|분기|연간|누계",
    re.I,
)
KOREAN_DAY = re.compile(
    r"\s*\d{1,2}월\s*\d{1,2}일\s*(?:\([월화수목금토일]\))?\s*"
)


def date_axis(rows, index, row):
    found, seen = {}, set()
    for cell in sorted((cell for cell in row if is_date(cell.get("value"))), key=column):
        key = _date_key(cell["value"])
        if key in seen:
            continue
        seen.add(key)
        found[column(cell)] = cell
    if len(found) < 2 or _reporting_basis(rows, index, found):
        return None
    return index, dict(list(found.items())[:7])


def is_date(value):
    return date_value(value) is not None or (
        isinstance(value, str) and bool(KOREAN_DAY.fullmatch(value))
    )


def column(cell):
    return column_index_from_string(coordinate_from_string(cell["cell"])[0])


def _date_key(value):
    parsed = date_value(value)
    return parsed.isoformat() if parsed else " ".join(str(value).split())


def _reporting_basis(rows, index, dates):
    if index == 0:
        return False
    previous = {column(cell): str(cell.get("value", "")).strip()
                for cell in rows[index - 1]}
    labels = [previous.get(position, "") for position in dates]
    return all(labels) and any(BASIS_HEADER.search(label) for label in labels)
