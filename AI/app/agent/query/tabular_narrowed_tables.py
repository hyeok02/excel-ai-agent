"""Regions the catalog cannot type as they stand: a title above, notes below, years as headers.

"Percentage of days …" / Year, Good, … / "Data: EPA …" is a table with a title
above its header and notes under its last record. Such a region is narrowed to
its header row and record rows and is then built and checked exactly like any
other table. A header may name periods with whole numbers (Indicator, 1997,
1998, … 2024): the years become that table's column names "1997", "1998", …, so
"2019년" maps onto the 2019 column for questions and edits alike.
"""
from openpyxl.utils import coordinate_to_tuple, get_column_letter, range_boundaries

from app.agent.query.tabular_catalog_builder import build_table
from app.agent.query.tabular_catalog_sources import cell_value

TITLE_ROWS = 4
YEARS = (1800, 2200)


def narrowed_table(sheet_name, reference, cells, complete, merged, hidden):
    """The region's table without its title and notes, or None."""
    narrowed = _narrowed(reference, cells)
    return build_table(sheet_name, narrowed, _year_names(narrowed, cells), complete, merged, hidden) if narrowed else None


def has_numbers(table):
    """A data table under a title, not a block of notes or links."""
    return any(isinstance(value, (int, float)) and not isinstance(value, bool)
               for row in table.rows for value in row.values.values())


def _narrowed(reference, cells):
    """Header = first row (among the top few) with two text labels; records end before trailing notes."""
    left, top, right, bottom = range_boundaries(reference)
    filled = {}
    for address, raw in sorted(cells.items(), key=lambda item: coordinate_to_tuple(item[0])):
        row, column = coordinate_to_tuple(address)
        if top <= row <= bottom and left <= column <= right and cell_value(raw) not in (None, ""):
            filled.setdefault(row, []).append(cell_value(raw))
    header = next((row for row in range(top, min(bottom, top + TITLE_ROWS) + 1)
                   if sum(isinstance(value, str) for value in filled.get(row, [])) >= 2
                   or _labels_and_years(filled.get(row, []))), None)
    last = max((row for row, values in filled.items() if len(values) >= 2), default=None)
    if header is None or last is None or last <= header or (header, last) == (top, bottom):
        return None
    return f"{get_column_letter(left)}{header}:{get_column_letter(right)}{last}"


def _labels_and_years(values):
    """A row label followed by increasing whole-number years: Indicator, 1997, 1998, …"""
    numbers = [value for value in values if not isinstance(value, str)]
    return (any(isinstance(value, str) for value in values) and len(numbers) >= 2
            and all(_year(value) for value in numbers) and all(a < b for a, b in zip(numbers, numbers[1:])))


def _year(value):
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and float(value).is_integer() and YEARS[0] <= value <= YEARS[1])


def _year_names(reference, cells):
    """Whole-number year headers read as the column names "1997", "1998", …"""
    left, top, right, _ = range_boundaries(reference)
    named = dict(cells)
    for column in range(left, right + 1):
        address = f"{get_column_letter(column)}{top}"
        raw = cells.get(address, {})
        if not raw.get("formula") and _year(raw.get("value")):
            named[address] = {**raw, "value": str(int(raw["value"]))}
    return named


def overlaps(first, second):
    a, b, c, d = range_boundaries(first)
    e, f, g, h = range_boundaries(second)
    return a <= g and e <= c and b <= h and f <= d
