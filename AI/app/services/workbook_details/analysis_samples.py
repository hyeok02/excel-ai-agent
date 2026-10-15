"""Bounded source samples independent of the small visual table preview."""
import os

from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.services.workbook_details.cell_values import formula_text, json_value, string_or_none
from app.services.workbook_details.models import CellValue


def _cap(name: str, default: int) -> int:
    """운영에서 파일 크기에 맞춰 조절할 수 있게 상한을 환경변수로 뺀다."""
    try:
        value = int(os.getenv(name, ""))
    except ValueError:
        return default
    return value if value > 0 else default


# 200행 15열짜리 점검표만 해도 3000셀이다. 상한이 2048이면 이런 평범한 업무
# 파일이 상한에 걸려 분석이 불완전해진다. 3만셀 워크북으로 재어 보니 상한을
# 올려도 파싱 시간과 API 응답 크기는 그대로고 요청당 메모리만 5MB 늘었다.
MAX_ANALYSIS_REGION_CELLS = _cap("ANALYSIS_MAX_REGION_CELLS", 16_384)
MAX_ANALYSIS_SHEET_CELLS = _cap("ANALYSIS_MAX_SHEET_CELLS", 16_384)
MAX_ANALYSIS_SCAN_CELLS = _cap("ANALYSIS_MAX_SCAN_CELLS", 200_000)


def analysis_cell_index(worksheet: Worksheet) -> dict[int, list[tuple[int, object]]]:
    index: dict[int, list[tuple[int, object]]] = {}
    for (row, column), cell in getattr(worksheet, "_cells", {}).items():
        index.setdefault(row, []).append((column, cell))
    return {
        row: sorted(index[row], key=lambda item: item[0])
        for row in sorted(index)
    }


def collect_analysis_rows(
    worksheet: Worksheet,
    value_worksheet: Worksheet | None,
    bounds: tuple[int, int, int, int],
    remaining_cells: int,
) -> list[list[dict[str, CellValue]]]:
    rows, _ = collect_analysis_sample(
        worksheet, value_worksheet, bounds, remaining_cells
    )
    return rows


def collect_analysis_sample(
    worksheet: Worksheet,
    value_worksheet: Worksheet | None,
    bounds: tuple[int, int, int, int],
    remaining_cells: int,
    hidden_rows: set[int] | None = None,
    hidden_columns: set[str] | None = None,
    cell_index: dict[int, list[tuple[int, object]]] | None = None,
    cached_cells: dict[tuple[int, int], object] | None = None,
) -> tuple[list[list[dict[str, CellValue]]], bool]:
    """Collect a complete dense or sparse sample within fixed scan/storage caps."""
    min_column, min_row, max_column, max_row = bounds
    limit = min(MAX_ANALYSIS_REGION_CELLS, remaining_cells)
    hidden_rows = hidden_rows or set()
    hidden_columns = {str(column).upper() for column in (hidden_columns or set())}
    if max_column < min_column or max_row < min_row or limit <= 0:
        return [], False
    cell_index = cell_index or analysis_cell_index(worksheet)
    if cached_cells is None:
        cached_cells = (
            getattr(value_worksheet, "_cells", {})
            if value_worksheet is not None else {}
        )
    rows, values, stored, scanned, complete = [], [], 0, 0, True
    for row, cells in cell_index.items():
        if row < min_row:
            continue
        if row > max_row:
            break
        if row in hidden_rows:
            continue
        for column, cell in cells:
            if not min_column <= column <= max_column:
                continue
            if _column_name(column) in hidden_columns:
                continue
            scanned += 1
            if scanned > MAX_ANALYSIS_SCAN_CELLS:
                complete = False
                break
            value = _analysis_cell(cell, cached_cells.get((row, column)))
            if not _populated(value):
                continue
            if stored >= limit:
                # 상한에 걸렸다고 읽은 셀까지 버리면 그 영역은 분석에서 통째로
                # 사라진다. 읽은 만큼 넘기고 불완전하다고 알리는 쪽이 낫다.
                complete = False
                break
            values.append(value)
            stored += 1
        if values:
            rows.append(values)
            values = []
        if not complete:
            break
    return rows, complete


def _column_name(column: int) -> str:
    return get_column_letter(column)


def _populated(cell: dict[str, CellValue]) -> bool:
    value = cell.get("cached_value") if cell.get("formula") else cell.get("value")
    return cell.get("formula") is not None or value not in (None, "")


def _analysis_cell(cell: object, value_cell: object | None) -> dict[str, CellValue]:
    raw_value = getattr(cell, "value", None)
    formula = formula_text(raw_value)
    is_formula = formula is not None
    result = {
        "address": str(getattr(cell, "coordinate")),
        "value": None if is_formula else json_value(raw_value),
        "formula": formula,
        "cached_value": json_value(getattr(value_cell, "value", None)) if is_formula else None,
        "number_format": string_or_none(getattr(cell, "number_format", None)),
        "bold": bool(getattr(getattr(cell, "font", None), "bold", False)),
    }
    hyperlink = getattr(cell, "hyperlink", None)
    if hyperlink is not None:
        result["hyperlink"] = getattr(hyperlink, "target", None)
    return result
