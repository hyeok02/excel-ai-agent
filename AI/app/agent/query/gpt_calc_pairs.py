"""Values written beside their names outside any table ('Net Monthly Check Amount | 4,000' above a budget),
offered to the GPT-chosen calculation as a small table of their own: 항목 | 값, by the columns they sit in."""
import re

from openpyxl.utils.cell import column_index_from_string, get_column_letter, range_boundaries

from app.agent.query.tabular_catalog_models import QueryColumn, QueryRow, QueryTable

MAX_PAIRS = 30  # more name-number rows than this are a list of records, not a form's values


def pair_tables(tables, index):
    covered = {}
    for table in tables:
        if table.source_kind == "stacked":
            continue
        left, top, right, bottom = range_boundaries(table.reference)
        covered.setdefault(table.sheet_name, []).append((left, top, right, bottom))
    groups = {}
    for row in index.rows:
        cells = {re.match(r"[A-Z]+", cell.address).group(0): cell for cell in row.cells if cell.value not in (None, "")}
        numbers = [letter for letter, cell in cells.items() if _number(cell.value)]
        if len(numbers) != 1 or (value := numbers[0]) == "A":
            continue
        name = get_column_letter(column_index_from_string(value) - 1)
        label = cells.get(name)
        inside = any(left <= column_index_from_string(name) <= right and top <= row.row_number <= bottom
                     for left, top, right, bottom in covered.get(row.sheet_name, []))
        if label is not None and isinstance(label.value, str) and label.value.strip() and not inside:
            groups.setdefault((row.sheet_name, name, value), []).append((row.row_number, label, cells[value]))
    found = []
    for (sheet, name, value), pairs in ((key, block) for key, every in groups.items() for block in _blocks(every)):
        if not 2 <= len(pairs) <= MAX_PAIRS:
            continue
        top, bottom = pairs[0][0], pairs[-1][0]
        rows = tuple(QueryRow(number, {name: label.value.strip(), value: cell.value},
                              number_formats={value: cell.number_format}) for number, label, cell in pairs)
        columns = (QueryColumn(id=name, header="항목", header_reference=f"{sheet}!{name}{top}",
                               sample_values=tuple(label.value.strip() for _, label, _ in pairs[:6])),
                   QueryColumn(id=value, header="값", header_reference=f"{sheet}!{value}{top}",
                               sample_values=tuple(cell.value for _, _, cell in pairs[:6])))
        found.append(QueryTable(id=f"pairs:{sheet}!{name}{top}", sheet_name=sheet, reference=f"{name}{top}:{value}{bottom}",
                                columns=columns, rows=rows, complete=True, source_kind="pairs"))
    return found


def _blocks(pairs, gap=3):
    """Pairs a few rows apart are one block ('Net Biweekly' · 'Net Monthly' · 'How much'); far apart, two."""
    blocks = [[pairs[0]]]
    for pair in pairs[1:]:
        if pair[0] - blocks[-1][-1][0] <= gap:
            blocks[-1].append(pair)
        else:
            blocks.append([pair])
    return blocks


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)
