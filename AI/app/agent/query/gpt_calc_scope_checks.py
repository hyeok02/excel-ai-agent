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
        if any(str(year) in str(item.value) for item in calc.filters for year in named & years) or names & {
                " ".join(name.split()).casefold() for name in calc.group_by}:
            return None  # a filter holding the year asked ('2025' for 2026 is another year's total)
        return (f"The question names {sorted(named & years)}, but the plan does not keep that year's rows in "
                f"{column.header}: filter that column to the year (op year, or ge/lt on its dates).")
    return None


def still_missing(question, table, calc, headings):
    """A retried plan that still leaves out a named value, year or section is not run: its total is another's."""
    from app.agent.query.gpt_calc_checks import unused_values
    return bool(unused_values(question, table, calc) or year_problem(question, table, calc)
                or section_problem(question, calc, headings))


def section_problem(question, calc, headings):
    """'2026년' naming one section of year headings that no filter of the plan keeps (under '2025년' is not it)."""
    from app.agent.query.ambiguity_labels import distinct_sheet_mentioned
    named = distinct_sheet_mentioned((headings or {}).values(), question)
    return bool(named) and not any(any(name in str(item.value) or str(item.value) in name for name in named)
                                   for item in calc.filters)  # 'under 2025년' for 2026년 is the wrong section


def in_scope(cells, scopes):
    """Only the cells inside a range the question names."""
    bounds = [(sheet, range_boundaries(area.replace("$", ""))) for sheet, area in scopes]
    return {reference: cell for reference, cell in cells.items() if any(
        sheet == getattr(cell, "sheet_name", None) and _inside(getattr(cell, "address", ""), box) for sheet, box in bounds)}


_AREA = re.compile(r"(?:'([^']+)'|([^\s\[\]()+\-*/,!']+))!\$?([A-Za-z]{1,3}\$?\d+)(?::\$?([A-Za-z]{1,3}\$?\d+))?")


def outside_scope(expression, scopes):
    """Cells or ranges of a formula plan that reach past the range the question names: SUM(Sales!D2:D7) for A1:D3."""
    bounds = [(sheet, range_boundaries(area.replace("$", ""))) for sheet, area in scopes]
    found = []
    bracketed = [(name, area) for name, area in re.findall(r"\[([^\[\]]+?)!([^\[\]!]+)\]", expression)]
    plain = [(match.group(1) or match.group(2), match.group(0).rpartition("!")[2])
             for match in _AREA.finditer(re.sub(r"\[[^\[\]]*\]", " ", expression))]  # [Cost variations!B4] keeps its space
    for name, area in bracketed + plain:
        sheet, corners = name.strip().strip("'"), [corner.replace("$", "").upper() for corner in area.split(":")]
        if not any(sheet == name and all(_inside(corner, box) for corner in corners) for name, box in bounds):
            found.append(f"{sheet}!{area}")
    return found


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
