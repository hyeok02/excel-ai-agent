from app.agent.contracts import AgentToolMetadata
from app.services.workbook_parsing.models import WorkbookSummary


def build_planning_context(
    summary: WorkbookSummary,
    tools: tuple[AgentToolMetadata, ...],
) -> dict[str, object]:
    dependencies = summary.dependency_summary
    risks = summary.formula_risk_summary
    return {
        "workbook": {
            "filename": summary.filename,
            "included_sheet_count": summary.sheet_count,
            "excluded_sheet_count": summary.excluded_sheet_count,
            "sheets": [
                {
                    "name": sheet.name,
                    "role": _wire_value(
                        sheet.sheet_classification.role
                        if sheet.sheet_classification
                        else None
                    ),
                    "importance": _wire_value(
                        sheet.sheet_classification.importance
                        if sheet.sheet_classification
                        else None
                    ),
                    "region_count": sheet.region_count,
                    "formula_count": sheet.formula_count,
                    "table_count": sheet.table_count,
                    "chart_count": sheet.chart_count,
                }
                for sheet in summary.sheets
            ],
            "dependency_overview": {
                "formula_node_count": dependencies.formula_node_count,
                "cross_sheet_edge_count": dependencies.cross_sheet_edge_count,
                "cycle_count": dependencies.cycle_count,
            },
            "risk_overview": {
                "total_count": risks.total_count,
                "error_count": risks.error_count,
                "warning_count": risks.warning_count,
            },
        },
        "available_tools": [
            {
                "name": tool.name,
                "description": tool.description,
                "capabilities": list(tool.capabilities),
                "input_schema": dict(tool.input_schema),
            }
            for tool in tools
        ],
    }


def _wire_value(value: object | None) -> object | None:
    return getattr(value, "value", value)
