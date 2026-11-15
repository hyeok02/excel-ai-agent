"""A table's own header of consecutive years that nothing labels as years.

"Region | 2019 | 2020 | 2021 | 2022" reads as years, but so could product codes laid out
the same way. Such a header is read as years only with its table's shape for support, and a
series read along it always states that reading ("해석: 머리글 2019~2022를 연도로 읽어 계산").
A left header naming codes (ID, Code, Product, SKU, Model, Part number) is never read so.
"""
import re

from app.services.insights.display.display_quality import is_identifier_label

_CODE_HEADER = re.compile(
    r"\b(?:ids?|codes?|sku|products?|models?|parts?|serial|zip|postal|item\s*(?:no|number|#))\b"
    r"|코드|번호|상품|제품|모델|품번|부품|우편", re.I)
_NUMBER = (int, float)


def unlabeled_year_header(row, cells, rows, years):
    """True when consecutive years head a table of text-labeled numeric rows; years: column -> (year, ...)."""
    columns = sorted(column for column, value in years.items() if value and not value[1])
    if len(columns) < 3 or columns != list(range(columns[0], columns[0] + len(columns))):
        return False
    values = [years[column][0] for column in columns]
    steps = {right - left for left, right in zip(values, values[1:])}
    if len(steps) != 1 or not 1 <= abs(next(iter(steps))) <= 10:
        return False
    left = [cells[column] for column in sorted(cells) if column < columns[0]]
    if not left or any(column > columns[-1] for column in cells):
        return False
    if not all(isinstance(cell.get("value"), str) and cell["value"].strip()
               and not _CODE_HEADER.search(cell["value"]) and not is_identifier_label(cell["value"])
               for cell in left):
        return False
    below = rows.get(row + 1, {})
    if not below or min(below) >= columns[0] or not isinstance(below[min(below)].get("value"), str):
        return False
    numbers = [below.get(column, {}).get("value") for column in columns]
    return sum(isinstance(value, _NUMBER) and not isinstance(value, bool) for value in numbers) >= 2


def year_like_header_cells(values):
    """Cells of an unlabeled row naming 2019 · 2020 · 2021: names, written as the source writes them, not 2,019."""
    if any(cell.get("label") for cell in values):
        return set()
    run = [cell for cell in values if isinstance(cell.get("value"), int) and not isinstance(cell.get("value"), bool)
           and 1000 <= cell["value"] <= 2999]
    steps = {right["value"] - left["value"] for left, right in zip(run, run[1:])}
    consecutive = len(run) >= 3 and len(steps) == 1 and 1 <= abs(next(iter(steps))) <= 10
    return {cell["cell"] for cell in run} if consecutive else set()
