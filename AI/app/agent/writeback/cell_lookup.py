"""Per-proposal lookups so checking N changed cells does not rescan the workbook N times.

A rule can reach thousands of rows. Finding each cell's neighbours, the formulas
that read it and the sheet's used area used to walk every indexed cell per change,
which made a 1,000-row edit take minutes. The same answers are read here from maps
built once: rows by sheet and number, and formula references by the cell or range
they read. Formula reading follows the rules of references._formula_references.
"""
import re
from collections import defaultdict

from app.agent.writeback.formula_ranges import SHEET_RANGE, covers, plain_ranges, sheet_ranges
from app.agent.writeback.models import WritebackContextCell
from app.agent.writeback.references import column_number

QUALIFIED_CELL = re.compile(r"(?:'([^']+)'|([A-Z_][A-Z0-9_. ]*))!([A-Z]{1,3}[0-9]{1,7})(?![A-Z0-9_:(])", re.I)
PLAIN_CELL = re.compile(r"(?<![A-Z0-9_!])([A-Z]{1,3}[0-9]{1,7})(?![A-Z0-9_(])", re.I)
MAX_AFFECTED = 12


class CellLookup:
    def __init__(self, data_index):
        self.rows = {(row.sheet_name, row.row_number): row for row in data_index.rows}
        self.bounds = defaultdict(lambda: (0, 0))
        self.readers = defaultdict(list)   # (sheet, CELL) -> formula cell references
        self.ranges = defaultdict(list)    # sheet -> [(span, formula cell reference)]
        for row in data_index.rows:
            last_row, last_column = self.bounds[row.sheet_name]
            columns = [column_number(cell.address) for cell in row.cells]
            self.bounds[row.sheet_name] = (max(last_row, row.row_number), max([last_column, *columns]))
            for cell in row.cells:
                if cell.formula:
                    self._read(cell)

    def _read(self, cell):
        formula = cell.formula.replace("$", "")
        for quoted, bare, target in QUALIFIED_CELL.findall(formula):
            self.readers[((quoted or bare).casefold(), target.upper())].append(cell)
        for sheet, span in sheet_ranges(formula):
            self.ranges[sheet.casefold()].append((span, cell))
        own = cell.sheet_name.casefold()
        unqualified = QUALIFIED_CELL.sub(" ", SHEET_RANGE.sub(" ", formula))
        for target in PLAIN_CELL.findall(unqualified):
            self.readers[(own, target.upper())].append(cell)
        for span in plain_ranges(formula):
            self.ranges[own].append((span, cell))

    def affected(self, sheet_name, reference):
        target = reference.replace("$", "").upper()
        column, row = column_number(target), int(re.search(r"\d+", target).group())
        sheet = sheet_name.casefold()
        found = [*self.readers.get((sheet, target), []),
                 *(cell for span, cell in self.ranges.get(sheet, []) if covers(span, column, row))]
        own = (sheet_name, target)
        return list(dict.fromkeys(cell.reference for cell in found
                                  if (cell.sheet_name, cell.address) != own))[:MAX_AFFECTED]

    def cell(self, sheet_name, reference):
        row = self.rows.get((sheet_name, int(re.search(r"\d+", reference).group())))
        return next((item for item in row.cells if item.address == reference.upper()), None) if row else None

    def context(self, target):
        target_column = column_number(target.address)
        target_row = int(re.search(r"\d+", target.address).group())
        candidates = []
        for number in (target_row - 1, target_row, target_row + 1):
            row = self.rows.get((target.sheet_name, number))
            for cell in row.cells if row else ():
                distance = abs(number - target_row) * 3 + abs(column_number(cell.address) - target_column)
                if cell.address != target.address and distance <= 4:
                    candidates.append((distance, number, column_number(cell.address), cell))
        candidates.sort(key=lambda item: item[:3])
        return [WritebackContextCell(reference=item[3].address, value=item[3].value) for item in candidates[:5]]
