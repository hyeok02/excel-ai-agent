from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm"}


class InvalidWorkbookError(ValueError):
    """Raised when an uploaded file cannot be parsed as a supported workbook."""


@dataclass(frozen=True)
class SheetSummary:
    name: str
    rows: int
    columns: int
    formula_count: int
    table_count: int
    chart_count: int


@dataclass(frozen=True)
class WorkbookSummary:
    filename: str
    sheet_count: int
    sheets: list[SheetSummary]


def parse_workbook(filename: str, content: bytes) -> WorkbookSummary:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise InvalidWorkbookError(".xlsx 또는 .xlsm 파일만 업로드할 수 있습니다.")

    try:
        workbook = load_workbook(
            BytesIO(content),
            data_only=False,
            keep_vba=extension == ".xlsm",
        )
    except (BadZipFile, InvalidFileException, KeyError, OSError, ValueError) as exception:
        raise InvalidWorkbookError("올바른 Excel 파일이 아닙니다.") from exception

    try:
        sheets = [
            SheetSummary(
                name=worksheet.title,
                rows=worksheet.max_row,
                columns=worksheet.max_column,
                formula_count=sum(
                    1
                    for row in worksheet.iter_rows()
                    for cell in row
                    if cell.data_type == "f"
                ),
                table_count=len(worksheet.tables),
                chart_count=len(worksheet._charts),
            )
            for worksheet in workbook.worksheets
        ]
    finally:
        workbook.close()

    return WorkbookSummary(
        filename=filename,
        sheet_count=len(sheets),
        sheets=sheets,
    )
