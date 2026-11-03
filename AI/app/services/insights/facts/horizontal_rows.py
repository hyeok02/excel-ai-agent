"""Normalize source region cells into one address-keyed worksheet view."""
from collections import defaultdict

from openpyxl.utils.cell import coordinate_from_string, column_index_from_string


def worksheet_rows(regions):
    rows = defaultdict(dict)
    for region in regions:
        for source_row in region.get("analysis_rows") or region.get("preview_rows", []):
            for cell in source_row:
                address = str(cell.get("address", ""))
                if not address:
                    continue
                column, row = coordinates(address)
                value = raw(cell)
                if value not in (None, ""):
                    rows[row][column] = {
                        "cell": address, "value": value,
                        "number_format": cell.get("number_format"),
                    }
    return rows


def raw(cell):
    return cell.get("cached_value") if cell.get("formula") else cell.get("value")


def coordinates(address):
    column, row = coordinate_from_string(address.replace("$", ""))
    return column_index_from_string(column), row
