from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from app.services.formula_analyzer import FormulaAnalysis, analyze_formulas
from app.services.region_detector import detect_regions
from app.services.workbook_details import (
    ChartSummary,
    RegionSummary,
    TableSummary,
    summarize_charts,
    summarize_regions,
    summarize_tables,
)

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
    formulas: list[FormulaAnalysis]
    region_count: int
    regions: list[RegionSummary]
    tables: list[TableSummary] = field(default_factory=list)
    charts: list[ChartSummary] = field(default_factory=list)


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
        sheets = []
        for worksheet in workbook.worksheets:
            formulas = analyze_formulas(worksheet)
            detected_regions = detect_regions(worksheet)
            regions = summarize_regions(worksheet, detected_regions)
            tables = summarize_tables(worksheet)
            charts = summarize_charts(workbook, worksheet)
            sheets.append(
                SheetSummary(
                    name=worksheet.title,
                    rows=worksheet.max_row,
                    columns=worksheet.max_column,
                    formula_count=len(formulas),
                    table_count=len(tables),
                    chart_count=len(charts),
                    formulas=formulas,
                    region_count=len(regions),
                    regions=regions,
                    tables=tables,
                    charts=charts,
                )
            )
    finally:
        workbook.close()

    return WorkbookSummary(
        filename=filename,
        sheet_count=len(sheets),
        sheets=sheets,
    )
