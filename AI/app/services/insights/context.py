from dataclasses import asdict

from app.services.analysis_strategy import AnalysisProfile, STANDARD_PROFILE
from app.services.insights.samples import (
    MAX_REFERENCES_PER_FORMULA,
    select_formula_samples,
    select_region_samples,
    truncate_formula,
)
from app.services.workbook_parser import WorkbookSummary


def build_workbook_context(
    summary: WorkbookSummary,
    profile: AnalysisProfile = STANDARD_PROFILE,
) -> dict[str, object]:
    sheets = [_sheet_context(sheet, profile) for sheet in summary.sheets[:profile.max_sheets]]
    dependencies = summary.dependency_summary
    return {
        "filename": summary.filename,
        "sheet_count": summary.sheet_count,
        "total_sheet_count": summary.total_sheet_count or summary.sheet_count,
        "excluded_sheet_count": summary.excluded_sheet_count,
        "excluded_sheets": [asdict(sheet) for sheet in summary.excluded_sheets],
        "included_sheet_count": len(sheets),
        "omitted_sheet_count": max(0, len(summary.sheets) - profile.max_sheets),
        "dependency_summary": {
            "node_count": dependencies.node_count,
            "edge_count": dependencies.edge_count,
            "formula_node_count": dependencies.formula_node_count,
            "cross_sheet_edge_count": dependencies.cross_sheet_edge_count,
            "named_reference_count": dependencies.named_reference_count,
            "external_reference_count": dependencies.external_reference_count,
            "cluster_count": dependencies.cluster_count,
            "cycle_count": dependencies.cycle_count,
            "cyclic_node_count": dependencies.cyclic_node_count,
            "largest_clusters": [
                {
                    "node_count": cluster.node_count,
                    "edge_count": cluster.edge_count,
                    "formula_count": cluster.formula_count,
                    "sheet_names": cluster.sheet_names,
                }
                for cluster in dependencies.clusters[:5]
            ],
        },
        "sheets": sheets,
    }


def _sheet_context(sheet: object, profile: AnalysisProfile) -> dict[str, object]:
    sheet_data = asdict(sheet)
    formulas = sheet_data.pop("formulas")
    regions = sheet_data.pop("regions")
    tables = sheet_data.pop("tables")
    charts = sheet_data.pop("charts")
    selected_formulas = select_formula_samples(formulas, profile.max_formulas_per_sheet)
    sheet_data["formula_samples"] = [
        {
            "cell": formula["cell"],
            "formula": truncate_formula(formula["formula"]),
            "references": formula["references"][:MAX_REFERENCES_PER_FORMULA],
        }
        for formula in selected_formulas
    ]
    sheet_data["omitted_formula_count"] = max(0, len(formulas) - len(selected_formulas))
    sheet_data["region_samples"] = select_region_samples(
        regions, profile.max_regions_per_sheet
    )
    sheet_data["omitted_region_count"] = max(
        0, len(regions) - profile.max_regions_per_sheet
    )
    sheet_data["table_samples"] = [
        {
            "name": table["name"],
            "reference": table["reference"],
            "headers": table["headers"],
            "row_count": table["row_count"],
            "column_count": table["column_count"],
        }
        for table in tables[:profile.max_tables_per_sheet]
    ]
    sheet_data["chart_samples"] = [
        {
            "title": chart["title"],
            "chart_type": chart["chart_type"],
            "anchor_cell": chart["anchor_cell"],
            "series_count": chart["series_count"],
        }
        for chart in charts[:profile.max_charts_per_sheet]
    ]
    return sheet_data
