import re

from openpyxl.utils.cell import get_column_letter, range_boundaries

from app.agent.query.index import WorkbookDataIndex
from app.agent.writeback.models import WritebackContextCell

MAX_CHANGES = 50
CELL_REFERENCE = re.compile(r"^[A-Z]{1,3}[1-9][0-9]{0,6}$")
CELL_RANGE = re.compile(
    r"^[A-Z]{1,3}[1-9][0-9]{0,6}:[A-Z]{1,3}[1-9][0-9]{0,6}$"
)


def expand_reference(reference: str) -> list[str]:
    normalized = reference.strip().upper().replace("$", "")
    if CELL_REFERENCE.fullmatch(normalized):
        return [normalized]
    if not CELL_RANGE.fullmatch(normalized):
        return []
    try:
        min_col, min_row, max_col, max_row = range_boundaries(normalized)
    except ValueError:
        return []
    count = (max_col - min_col + 1) * (max_row - min_row + 1)
    if count > MAX_CHANGES:
        return ["__TOO_LARGE__"] * (MAX_CHANGES + 1)
    return [
        f"{get_column_letter(column)}{row}"
        for row in range(min_row, max_row + 1)
        for column in range(min_col, max_col + 1)
    ]


def affected_cells(
    data_index: WorkbookDataIndex, sheet_name: str, reference: str
) -> list[str]:
    affected = []
    target = reference.replace("$", "").upper()
    for row in data_index.rows:
        for cell in row.cells:
            if not cell.formula or (cell.sheet_name == sheet_name and cell.address == target):
                continue
            if _formula_references(cell.formula, cell.sheet_name, sheet_name, target):
                affected.append(cell.reference)
    return affected[:12]


def _formula_references(
    formula: str, formula_sheet: str, target_sheet: str, target: str
) -> bool:
    normalized = formula.replace("$", "")
    qualified = (
        f"'{target_sheet}'!{target}".casefold(),
        f"{target_sheet}!{target}".casefold(),
    )
    if any(item in normalized.casefold() for item in qualified):
        return True
    if formula_sheet.casefold() != target_sheet.casefold():
        return False
    pattern = rf"(?<![A-Z0-9_]){re.escape(target)}(?![A-Z0-9_])"
    if re.search(pattern, normalized, re.I):
        return True
    target_column = column_number(target)
    target_row = int(re.search(r"\d+", target).group())
    ranges = re.findall(
        r"([A-Z]{1,3}[1-9][0-9]{0,6}):([A-Z]{1,3}[1-9][0-9]{0,6})",
        normalized,
        re.I,
    )
    for start, end in ranges:
        min_col, min_row, max_col, max_row = range_boundaries(f"{start}:{end}")
        if min_col <= target_column <= max_col and min_row <= target_row <= max_row:
            return True
    return False


def context_cells(data_index, target) -> list[WritebackContextCell]:
    target_column = column_number(target.address)
    target_row = int(re.search(r"\d+", target.address).group())
    candidates = []
    for row in data_index.rows:
        if row.sheet_name != target.sheet_name or abs(row.row_number - target_row) > 1:
            continue
        for cell in row.cells:
            if cell.address == target.address:
                continue
            distance = abs(row.row_number - target_row) * 3 + abs(
                column_number(cell.address) - target_column
            )
            if distance <= 4:
                candidates.append(
                    (distance, row.row_number, column_number(cell.address), cell)
                )
    candidates.sort(key=lambda item: item[:3])
    return [
        WritebackContextCell(reference=item[3].address, value=item[3].value)
        for item in candidates[:5]
    ]


def column_number(reference: str) -> int:
    letters = re.match(r"[A-Z]+", reference.upper()).group()
    result = 0
    for letter in letters:
        result = result * 26 + ord(letter) - ord("A") + 1
    return result


def key(sheet_name: str, reference: str) -> str:
    return f"{sheet_name.casefold()}!{reference.upper()}"
