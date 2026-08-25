from collections import defaultdict

from openpyxl.workbook.workbook import Workbook

from app.services.analysis_inclusion import AnalysisInclusion
from app.services.formula_analyzer import FormulaAnalysis
from app.services.sheet_classification.classifier import classify_sheet
from app.services.sheet_classification.models import (
    SheetClassification,
    SheetImportance,
    SheetRole,
    SheetRoleReason,
)


def classify_sheets(
    workbook: Workbook,
    formulas_by_sheet: dict[str, list[FormulaAnalysis]],
    inclusions_by_sheet: dict[str, AnalysisInclusion],
) -> dict[str, SheetClassification]:
    referenced_sheets: dict[str, set[str]] = defaultdict(set)
    referenced_by_sheets: dict[str, set[str]] = defaultdict(set)
    workbook_sheet_names = set(workbook.sheetnames)
    for sheet_name, formulas in formulas_by_sheet.items():
        for formula in formulas:
            for reference in formula.references:
                referenced_sheet = _reference_sheet_name(reference)
                if (
                    referenced_sheet is None
                    or referenced_sheet == sheet_name
                    or referenced_sheet not in workbook_sheet_names
                ):
                    continue
                referenced_sheets[sheet_name].add(referenced_sheet)
                referenced_by_sheets[referenced_sheet].add(sheet_name)
    return {
        worksheet.title: classify_sheet(
            worksheet,
            formulas_by_sheet.get(worksheet.title, []),
            inclusions_by_sheet[worksheet.title],
            referenced_sheets[worksheet.title],
            referenced_by_sheets[worksheet.title],
        )
        for worksheet in workbook.worksheets
    }


def _reference_sheet_name(reference: str) -> str | None:
    if "[" in reference or "!" not in reference:
        return None
    sheet_token, _ = reference.rsplit("!", 1)
    sheet_name = sheet_token.strip()
    if sheet_name.startswith("'") and sheet_name.endswith("'"):
        sheet_name = sheet_name[1:-1].replace("''", "'")
    return sheet_name


__all__ = [
    "SheetClassification",
    "SheetImportance",
    "SheetRole",
    "SheetRoleReason",
    "classify_sheets",
]
