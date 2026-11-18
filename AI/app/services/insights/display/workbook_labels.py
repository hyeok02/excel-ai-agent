"""Prepare a workbook's Korean label readings before its report or answers are written."""
from hashlib import sha256

from app.services.insights.display.label_translator import prepare_labels


def prepare_workbook_labels(summary, translator=None):
    """One offline pass over the report and every series fact, then one reading call for unread labels."""
    if summary is None:
        return

    def render():
        from app.services.insights.facts.context import build_workbook_context
        from app.services.insights.narratives.all_series_facts import all_series_facts
        from app.services.insights.narratives.source_narratives import source_narrative_report
        context = build_workbook_context(summary)
        source_narrative_report(context)
        all_series_facts(context)

    shape = [summary.filename, *((sheet.name, sheet.rows, sheet.columns) for sheet in summary.sheets)]
    prepare_labels(sha256(repr(shape).encode()).hexdigest(), render, translator)
