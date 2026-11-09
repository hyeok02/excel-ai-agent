"""Currency a record column inherits from a native pivot that totals exactly that column.

FoodSales!TotalPrice holds plain numbers ("General"), while the CatReg pivot
sums that whole column and shows its total as $33,326. The pivot is the source's
own declaration of the unit, so answers show "$17,212.41" as the insights do.
The link follows the parser's native pivot source and field, and the pivot's
cached total must equal the column's sum over the complete table; a matching
number or a nearby caption is never enough. Only the currency is inherited, not
the pivot's rounding or scale, and a column with its own format keeps it.
"""
import math
from dataclasses import replace

from openpyxl.utils import range_boundaries

from app.services.insights.narratives.record_units import _currency


def linked_currencies(summary, table):
    """{column id: currency} for the table's columns a native pivot declares a currency for."""
    if not table.complete:
        return {}
    left, top, right, bottom = range_boundaries(table.reference)
    found = {}
    for sheet in summary.sheets:
        for source in getattr(sheet, "pivot_unit_sources", ()) or ():
            column = source.get("source_column")
            header = next((item.header for item in table.columns if item.id == column), None)
            if (source.get("source_sheet") != table.sheet_name or header is None
                    or source.get("source_header") != header):
                continue
            try:
                bounds = range_boundaries(source["source_range"])
            except (KeyError, TypeError, ValueError):
                continue
            values = [row.values.get(column) for row in table.rows]
            if (bounds != (left, top, right, bottom) or len(table.rows) != bottom - top
                    or any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in values)):
                continue
            cached = source.get("total_value")
            if not isinstance(cached, (int, float)) or not math.isclose(
                    math.fsum(values), cached, rel_tol=1e-12, abs_tol=1e-9):
                continue
            if currency := _currency(source.get("number_format")):
                found.setdefault(column, set()).add(currency)
    return {column: next(iter(units)) for column, units in found.items() if len(units) == 1}


def inherit_currencies(summary, table):
    """The table with linked currency columns shown with that currency."""
    currencies = linked_currencies(summary, table)
    if not currencies:
        return table
    rows = tuple(replace(row, number_formats={column: with_currency(style, currencies[column]) or style
                                              if column in currencies else style
                                              for column, style in row.number_formats.items()})
                 for row in table.rows)
    columns = tuple(replace(column, currency=currencies.get(column.id, "")) for column in table.columns)
    return replace(table, rows=rows, columns=columns)


def with_currency(number_format, currency):
    """The cell's own format with the inherited currency, or None when it has a unit already."""
    text = number_format or "General"
    if ";" in text or "%" in text or _currency(text) or text.casefold() != "general":
        return None
    return f'"{currency}"General' if len(currency) == 1 else f'"{currency} "General'
