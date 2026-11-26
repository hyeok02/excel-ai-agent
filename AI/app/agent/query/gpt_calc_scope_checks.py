"""A plan held to the years and the range the question names, whichever way it calculates.

"2023년 Boston 합계" over a list of 2022 and 2023 rows is 70, not Boston's 170 of both years: a plan with no
condition on the dates is sent back, and not run when it comes back the same. "Sales!A1:D3 범위" holds for a
plan of cell formulas as for a table plan: cells outside the range are not there to be read.
"""
import re
from datetime import date, datetime

from openpyxl.utils import range_boundaries
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

_YEAR = re.compile(r"(?<!\d)((?:19|20)\d{2})(?!\d)")


def year_problem(question, table, calc):
    """The years the question names that a plan over several years' rows leaves unfiltered, told back; else None."""
    named = {int(year) for year in _YEAR.findall(question)}
    if not named:
        return None
    for column in table.columns:
        years = {year for row in table.rows if (year := _year(row.values.get(column.id))) is not None}
        if len(years) < 2 or not named & years:
            continue
        names = {" ".join(str(column.header).split()).casefold(), column.id.casefold()}
        if any(" ".join(item.column.split()).casefold() in names or str(sorted(named)[0]) in str(item.value)
               for item in calc.filters) or names & {" ".join(name.split()).casefold() for name in calc.group_by}:
            return None
        return (f"The question names {sorted(named & years)}, but the plan keeps the rows of every year in "
                f"{column.header}: filter that column to the year (op year, or ge/lt on its dates).")
    return None


def in_scope(cells, scopes):
    """Only the cells inside a range the question names."""
    bounds = [(sheet, range_boundaries(area.replace("$", ""))) for sheet, area in scopes]
    return {reference: cell for reference, cell in cells.items() if any(
        sheet == getattr(cell, "sheet_name", None) and _inside(getattr(cell, "address", ""), box) for sheet, box in bounds)}


def _inside(address, box):
    try:
        letters, row = coordinate_from_string(address)
    except ValueError:
        return False
    left, top, right, bottom = box
    return left <= column_index_from_string(letters) <= right and top <= row <= bottom


def _year(value):
    if isinstance(value, (datetime, date)):
        return value.year
    if isinstance(value, str) and (found := re.match(r"\s*((?:19|20)\d{2})[-./]\d{1,2}", value)):
        return int(found[1])
    if isinstance(value, (int, float)) and not isinstance(value, bool) and float(value).is_integer() and 1900 <= value <= 2100:
        return int(value)
    return None
