from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from zipfile import BadZipFile

from openpyxl import load_workbook
from openpyxl.utils.exceptions import InvalidFileException

from app.services.dependency_analyzer import (
    DependencySummary,
    analyze_dependencies,
)
from app.services.analysis_inclusion import (
    AnalysisDecision,
    AnalysisInclusion,
    INCLUDED_BUSINESS_WORKSHEET,
)
from app.services.formula_analyzer import FormulaAnalysis, analyze_formulas
from app.services.region_detector import detect_regions
from app.services.sheet_classifier import SheetClassification, classify_sheets
from app.services.workbook_details import (
    ChartSummary,
    RegionSummary,
    TableSummary,
    summarize_charts,
    summarize_regions,
    summarize_tables,
)
from app.services.worksheet_filter import evaluate_worksheet_inclusion

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
    analysis_inclusion: AnalysisInclusion = INCLUDED_BUSINESS_WORKSHEET
    tables: list[TableSummary] = field(default_factory=list)
    charts: list[ChartSummary] = field(default_factory=list)
    sheet_classification: SheetClassification | None = None


@dataclass(frozen=True)
class ExcludedSheetSummary:
    name: str
    state: str
    analysis_inclusion: AnalysisInclusion
    sheet_classification: SheetClassification


@dataclass(frozen=True)
class WorkbookSummary:
    filename: str
    sheet_count: int
    sheets: list[SheetSummary]
    total_sheet_count: int = 0
    excluded_sheet_count: int = 0
    excluded_sheets: list[ExcludedSheetSummary] = field(default_factory=list)
    dependency_summary: DependencySummary = field(
        default_factory=DependencySummary.empty
    )


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
        value_workbook = load_workbook(
            BytesIO(content),
            data_only=True,
            keep_vba=extension == ".xlsm",
        )
    except (BadZipFile, InvalidFileException, KeyError, OSError, ValueError) as exception:
        raise InvalidWorkbookError("올바른 Excel 파일이 아닙니다.") from exception

    try:
        total_sheet_count = len(workbook.sheetnames)
        inclusions_by_sheet = {
            worksheet.title: evaluate_worksheet_inclusion(worksheet)
            for worksheet in workbook.worksheets
        }
        formulas_by_sheet = {
            worksheet.title: analyze_formulas(
                worksheet,
                value_workbook[worksheet.title],
            )
            for worksheet in workbook.worksheets
        }
        classifications_by_sheet = classify_sheets(
            workbook,
            formulas_by_sheet,
            inclusions_by_sheet,
        )
        sheets = []
        excluded_sheets = []
        for worksheet in workbook.worksheets:
            analysis_inclusion = inclusions_by_sheet[worksheet.title]
            sheet_classification = classifications_by_sheet[worksheet.title]
            if analysis_inclusion.decision is AnalysisDecision.EXCLUDE:
                excluded_sheets.append(
                    ExcludedSheetSummary(
                        name=worksheet.title,
                        state=worksheet.sheet_state,
                        analysis_inclusion=analysis_inclusion,
                        sheet_classification=sheet_classification,
                    )
                )
                continue

            value_worksheet = value_workbook[worksheet.title]
            formulas = formulas_by_sheet[worksheet.title]
            detected_regions = detect_regions(
                worksheet,
                sheet_role=sheet_classification.role.value,
            )
            regions = summarize_regions(worksheet, detected_regions, value_worksheet)
            tables = summarize_tables(worksheet, value_worksheet)
            charts = summarize_charts(workbook, worksheet, value_workbook)
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
                    analysis_inclusion=analysis_inclusion,
                    tables=tables,
                    charts=charts,
                    sheet_classification=sheet_classification,
                )
            )
    finally:
        workbook.close()
        value_workbook.close()

    dependency_summary = analyze_dependencies(
        [(sheet.name, sheet.formulas) for sheet in sheets]
    )

    return WorkbookSummary(
        filename=filename,
        sheet_count=len(sheets),
        sheets=sheets,
        total_sheet_count=total_sheet_count,
        excluded_sheet_count=len(excluded_sheets),
        excluded_sheets=excluded_sheets,
        dependency_summary=dependency_summary,
    )
