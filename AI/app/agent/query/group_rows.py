"""Heading rows that group the rows below them, read from the source's own formatting.

A table listing "New England" then its states, "Pacific Noncontiguous" then Alaska and Hawaii,
marks the headings by a fill, bold or indent the member rows do not have. Such rows are not
members: "states above 30 cents" must not list a census division. No words are matched: a row
is a heading when its label cell is styled unlike most rows and a plain row follows it.
"""
from collections import Counter

from app.agent.query.tabular_catalog_sources import source_cells

MAX_SHARE = 0.4  # more styled rows than this is banding or emphasis, not headings


def group_rows(table, summary):
    """{row number: label} of the table's heading rows, or {} when the formatting marks none."""
    label = next((column for column in table.columns if all(
        isinstance(row.values.get(column.id), str) for row in table.rows if row.values.get(column.id) not in (None, ""))),
        None)
    if label is None or len(table.rows) < 6:
        return {}
    sheet = next((item for item in summary.sheets if item.name == table.sheet_name), None)
    if sheet is None:
        return {}
    cells = {address: cell for region in sheet.regions for address, cell in source_cells(region).items()}
    styles = {}
    for row in table.rows:
        cell = cells.get(f"{label.id}{row.row_number}") or {}
        styles[row.row_number] = (bool(cell.get("bold")), cell.get("fill"), cell.get("indent", 0))
    plain, _ = Counter(styles.values()).most_common(1)[0]
    marked = [number for number, style in styles.items() if style != plain]
    if not marked or len(marked) > len(styles) * MAX_SHARE:
        return {}
    numbers = sorted(styles)
    after = dict(zip(numbers, numbers[1:]))
    # Every heading is followed by a member row; a styled last row heads nothing (a latest month in bold).
    if any(number in after and styles[after[number]] != plain for number in marked):
        return {}
    marked = [number for number in marked if number in after]
    if not marked:
        return {}
    values = {row.row_number: row.values.get(label.id) for row in table.rows}
    return {number: str(values[number]) for number in marked}


def section_rows(table):
    """{row number: label} of rows naming a section and holding nothing else ("Year 2026" over its months).

    Read from the values: the row's only value is a text in its first column, in a table of three or more
    columns, and a fuller row follows it. Such rows head the rows below them like styled headings do.
    """
    if len(table.columns) < 3 or not table.rows:
        return {}
    first = table.columns[0].id
    filled = [[value for value in row.values.values() if value not in (None, "")] for row in table.rows]
    return {row.row_number: " ".join(row.values[first].split()) for number, row in enumerate(table.rows)
            if len(filled[number]) == 1 and isinstance(row.values.get(first), str) and row.values[first].strip()
            and number + 1 < len(table.rows) and len(filled[number + 1]) > 1}
