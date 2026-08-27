from openpyxl.workbook.workbook import Workbook

from app.services.analysis_inclusion import AnalysisDecision, AnalysisInclusion
from app.services.formula_analyzer import FormulaAnalysis
from app.services.region_detector import detect_regions
from app.services.sheet_classifier import SheetClassification
from app.services.workbook_details import (
    build_column_schemas,
    summarize_charts,
    summarize_regions,
    summarize_tables,
)
from app.services.workbook_parsing.models import ExcludedSheetSummary, SheetSummary
from app.services.workbook_parsing.provenance import (
    with_classification_provenance,
    with_inclusion_provenance,
)


def build_sheet_summaries(
    workbook: Workbook,
    value_workbook: Workbook,
    formulas_by_sheet: dict[str, list[FormulaAnalysis]],
    inclusions_by_sheet: dict[str, AnalysisInclusion],
    classifications_by_sheet: dict[str, SheetClassification],
) -> tuple[list[SheetSummary], list[ExcludedSheetSummary]]:
    sheets: list[SheetSummary] = []
    excluded: list[ExcludedSheetSummary] = []
    for worksheet in workbook.worksheets:
        inclusion = with_inclusion_provenance(
            worksheet.title, inclusions_by_sheet[worksheet.title]
        )
        classification = with_classification_provenance(
            worksheet.title, classifications_by_sheet[worksheet.title]
        )
        if inclusion.decision is AnalysisDecision.EXCLUDE:
            excluded.append(
                ExcludedSheetSummary(
                    worksheet.title,
                    worksheet.sheet_state,
                    inclusion,
                    classification,
                )
            )
            continue
        value_worksheet = value_workbook[worksheet.title]
        formulas = formulas_by_sheet[worksheet.title]
        detected = detect_regions(
            worksheet, sheet_role=classification.role.value
        )
        regions = summarize_regions(worksheet, detected, value_worksheet)
        column_schemas = build_column_schemas(
            worksheet, value_worksheet, detected, regions
        )
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
                column_schemas=column_schemas,
                analysis_inclusion=inclusion,
                tables=tables,
                charts=charts,
                sheet_classification=classification,
            )
        )
    return sheets, excluded
