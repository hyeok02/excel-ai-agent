from pathlib import Path

from app.services.dependency_analyzer import analyze_dependencies
from app.services.formula_analyzer import analyze_formulas
from app.services.formula_risks import detect_formula_risks
from app.services.sheet_classifier import classify_sheets
from app.services.workbook_parsing.models import (
    ExcludedSheetSummary,
    SheetSummary,
    WorkbookSummary,
)
from app.services.workbook_parsing.sheets import build_sheet_summaries
from app.services.worksheet_filter import evaluate_worksheet_inclusion
from app.services.workbook_loading import (
    InvalidWorkbookError, close_workbook, load_workbook_pair,
)

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm"}


def parse_workbook(filename: str, content: bytes) -> WorkbookSummary:
    extension = Path(filename).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        raise InvalidWorkbookError(".xlsx 또는 .xlsm 파일만 업로드할 수 있습니다.")
    workbook, value_workbook = load_workbook_pair(content, keep_vba=extension == ".xlsm")
    try:
        total_sheet_count = len(workbook.sheetnames)
        inclusions = {
            sheet.title: evaluate_worksheet_inclusion(sheet)
            for sheet in workbook.worksheets
        }
        formulas = {
            sheet.title: analyze_formulas(sheet, value_workbook[sheet.title])
            for sheet in workbook.worksheets
        }
        classifications = classify_sheets(workbook, formulas, inclusions)
        sheets, excluded = build_sheet_summaries(
            workbook,
            value_workbook,
            formulas,
            inclusions,
            classifications,
        )
        formula_risks = detect_formula_risks(
            workbook.sheetnames,
            [(sheet.name, sheet.formulas) for sheet in sheets],
            workbook.worksheets,
        )
    finally:
        close_workbook(workbook)
        close_workbook(value_workbook)
    dependencies = analyze_dependencies(
        [(sheet.name, sheet.formulas) for sheet in sheets]
    )
    return WorkbookSummary(
        filename=filename,
        sheet_count=len(sheets),
        sheets=sheets,
        total_sheet_count=total_sheet_count,
        excluded_sheet_count=len(excluded),
        excluded_sheets=excluded,
        dependency_summary=dependencies,
        formula_risk_summary=formula_risks,
    )


__all__ = [
    "ExcludedSheetSummary",
    "InvalidWorkbookError",
    "SheetSummary",
    "WorkbookSummary",
    "parse_workbook",
]
