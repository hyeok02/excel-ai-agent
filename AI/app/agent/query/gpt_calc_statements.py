"""Statement-like tables whose row names sit in a column with no header, read with those names.

A financial statement heads its year columns only ('2022A', '2023A', '2024A'): the row names ('Total net sales',
'Repurchases of common stock') stand in the column to their left under an empty header cell, and later
sections ('Balance Sheet:', 'Cash Flow') continue under the same year columns after a blank row. The table is
offered with that column (항목) and, when its columns are periods, with the sections below it.
"""
import re
from dataclasses import replace

from openpyxl.utils.cell import column_index_from_string, get_column_letter

from app.agent.query.tabular_catalog_models import QueryColumn, QueryRow

LABEL, GROUP, UNIT = "항목", "구분", "단위"
_PERIOD = re.compile(r"^(?:FY\s*'?\d{2,4}[AEFPB]?|(?:19|20)\d{2}\s*(?:년|[AEFPB])?|(?:19|20)\d{2}\s*[-./ ]?\s*(?:Q[1-4]|H[12]))$",
                     re.I)


def labeled_tables(tables, index):
    sheets = {}
    for row in index.rows:
        sheets.setdefault(row.sheet_name, {})[row.row_number] = {
            re.match(r"[A-Z]+", cell.address).group(0): cell for cell in row.cells}
    return [_labeled(table, sheets.get(table.sheet_name, {})) or table for table in tables]


def _labeled(table, rows):
    ids = [column.id for column in table.columns]
    if not ids or table.source_kind == "stacked" or not all(re.fullmatch(r"[A-Z]+", key) for key in ids):
        return None
    numbers = [row.row_number for row in table.rows]
    found = _label_columns(min(column_index_from_string(key) for key in ids), ids, numbers, rows)
    if found is None:
        return None
    names, unit, group = found
    reference = lambda letter: re.sub(r"[A-Z]+(?=\d+$)", letter, table.columns[0].header_reference)  # noqa: E731
    labels = {number: _name(rows.get(number, {}), names) for number in numbers}
    groups = _filled(rows, names[-1], min(numbers), max(numbers)) if group else {}
    columns = [QueryColumn(id=names[0], header=LABEL, header_reference=reference(names[0]),
                           sample_values=tuple(text for text in labels.values() if text)[:6])]
    columns += [QueryColumn(id=names[-1], header=GROUP, header_reference=reference(names[-1]),
                            sample_values=tuple(dict.fromkeys(text for text in groups.values() if text))[:6])] if group else []
    columns += [QueryColumn(id=unit, header=UNIT, header_reference=reference(unit),
                            sample_values=tuple(dict.fromkeys(_text(rows.get(n, {}).get(unit)) for n in numbers))[:6])] if unit else []
    extra = lambda number: {names[0]: labels.get(number, _name(rows.get(number, {}), names)), **(  # noqa: E731
        {names[-1]: groups.get(number)} if group else {}), **({unit: _text(rows.get(number, {}).get(unit))} if unit else {})}
    kept = [replace(row, values={**extra(row.row_number), **row.values}) for row in table.rows]
    periods = [column for column in table.columns if _PERIOD.match(" ".join(str(column.header).split()))]
    if len(periods) >= 2:  # 'Balance Sheet:' and 'Cash Flow' below, under the same year columns
        kept += [replace(row, values={**extra(row.row_number), **row.values})
                 for row in _sections(table, rows, names, [column.id for column in periods])]
    return replace(table, columns=(*columns, *table.columns), rows=tuple(kept))


def _label_columns(first, ids, numbers, rows):
    """(name columns right to left, a unit column or None, whether the leftmost name column groups the rest).

    The text columns left of the first value column: '원' · '개' repeated is a unit; a name per row is the item,
    and a name only at a group's first row (Living, then its lines) is the group the rows below belong to."""
    columns = []
    for index in range(first - 1, max(first - 5, 0), -1):
        letter = get_column_letter(index)
        texts = [_text(rows.get(number, {}).get(letter)) for number in numbers]
        if letter in ids or not any(texts):
            break
        columns.append((letter, [text for text in texts if text]))
    unit = next((letter for letter, texts in columns if len(texts) >= 0.6 * len(numbers)
                 and len(set(texts)) <= 5 < len(texts) + 3 and all(len(text) <= 3 for text in texts)), None)
    names = [letter for letter, _ in columns if letter != unit] or ([unit] if unit else [])  # 'KR' · 'US': names
    unit = unit if unit not in names else None
    if not names or sum(bool(_name(rows.get(number, {}), names)) for number in numbers) < max(2, 0.6 * len(numbers)):
        return None
    group = len(names) > 1 and len(dict(columns)[names[-1]]) < 0.5 * len(numbers)
    return names, unit, group


def _name(cells, names):
    return next((text for letter in names if (text := _text(cells.get(letter)))), None)


def _filled(rows, letter, top, bottom):
    """A group name carried down to the rows under it: Living over Mortgage/Rent … Cell Phone."""
    filled, current = {}, None
    for number in range(top, bottom + 1):
        current = _text(rows.get(number, {}).get(letter)) or current
        filled[number] = current
    return filled


def _text(cell):
    value = getattr(cell, "value", None)
    return value.strip() if isinstance(value, str) and value.strip() else None


def _sections(table, rows, names, years):
    """Rows below the table under its year columns, until a row writes text across them (another table's header)."""
    end, found = max(row.row_number for row in table.rows), []
    for number in sorted(key for key in rows if key > end):
        cells = rows[number]
        values = {key: cells[key].value for key in years if key in cells}
        if sum(isinstance(value, str) and value.strip() for value in values.values()) >= 2:
            break
        if values or _name(cells, names):
            found.append(QueryRow(number, values, number_formats={key: cells[key].number_format for key in values}))
    return found
