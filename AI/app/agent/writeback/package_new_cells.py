"""A blank cell an approved change fills: written into its row, among the row's cells in column order.

Excel leaves no <c> element for a cell that was never typed in. Filling '미정' into 공급사 G2 adds one to row 2,
before the first cell to its right, so the row keeps the order Excel requires; nothing else in the sheet moves.
"""
import re

from openpyxl.utils.cell import column_index_from_string, coordinate_from_string

_ROW = r"<(?P<q>(?:[\w.-]+:)?)row\b[^>]*?\br=\"{row}\"[^>]*?(?P<empty>/?)>"
_CELL = re.compile(rb"<(?:[\w.-]+:)?c\b[^>]*?\br=\"(?P<ref>[A-Z]+\d+)\"")


def new_cell_edit(xml, reference, serialized):
    """(position, position, column, bytes) inserting a cell into its row, or None when the row is not written."""
    letters, row = coordinate_from_string(reference.upper())
    found = re.search(_ROW.format(row=row).encode(), xml)
    if found is None:
        return None
    prefix = found.group("q").decode()
    cell_type, body = serialized(prefix)
    kind = f' t="{cell_type}"' if cell_type else ""
    element = f'<{prefix}c r="{reference.upper()}"{kind}>{body}</{prefix}c>'.encode("utf-8")
    column = column_index_from_string(letters)
    if found.group("empty"):
        return None  # a row written with no cell at all is left as it is
    close = xml.index(f"</{prefix}row>".encode(), found.end())
    position = close
    for cell in _CELL.finditer(xml, found.end(), close):
        if column_index_from_string(coordinate_from_string(cell.group("ref").decode())[0]) > column:
            position = cell.start()
            break
    return position, position, column, element
