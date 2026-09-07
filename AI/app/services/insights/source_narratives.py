"""Deterministic semantic facts; model prose may reuse them, not invent bindings."""
from app.services.insights.horizontal_trends import horizontal_trend_report
from app.services.insights.models import WorkbookInsightReport
from app.services.insights.ranked_narratives import ranked_report
from app.services.insights.sheet_scope import comparison_sheet
from app.services.insights.table_narratives import table_report
from app.services.insights.trend_narratives import trend_report
from app.services.insights.validation_index import extract_references


def source_narrative_report(context):
    options = []
    reporters = (trend_report, ranked_report, table_report, horizontal_trend_report)
    for mode_order, reporter in enumerate(reporters):
        items, overview = reporter(context)
        if items:
            comparison, source_order = _source_scope(context, items)
            options.append((comparison, source_order, mode_order, items, overview))
    if not options:
        return WorkbookInsightReport(overview="", insights=[], limitations=[])
    primary = [option for option in options if not option[0]]
    _, _, _, items, overview = min(primary or options, key=lambda option: option[1:3])
    return WorkbookInsightReport(overview=overview, insights=items, limitations=[])


def _source_scope(context, items):
    sheets = {
        str(sheet.get("name", "")).casefold(): (index, comparison_sheet(sheet))
        for index, sheet in enumerate(context.get("sheets", []))
        if isinstance(sheet, dict)
    }
    sources = []
    for item in items:
        for evidence in item.evidence:
            for ref in extract_references(str(evidence)):
                if ref.split("!", 1)[0] in sheets:
                    sources.append(sheets[ref.split("!", 1)[0]])
    return (all(source[1] for source in sources),
            min((source[0] for source in sources), default=len(sheets)))
