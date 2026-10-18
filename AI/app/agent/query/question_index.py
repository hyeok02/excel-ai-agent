"""Attach an original-source reader to Q&A only, never to writeback indexes."""
from dataclasses import replace

from app.agent.query.index import build_workbook_data_index
from app.agent.query.workbook_source import WorkbookSource
from app.agent.query.workbook_source_models import SourceReadLimits, SourceSheet


def build_question_data_index(filename, content, summary, *, limits=None):
    included = {sheet.name for sheet in summary.sheets}
    index = build_workbook_data_index(filename, content, included)
    sheets = tuple(SourceSheet(
        sheet.name, sheet.rows, sheet.columns,
        frozenset(row for region in sheet.regions for row in region.hidden_rows),
        frozenset(column for region in sheet.regions for column in region.hidden_columns),
        tuple(dict.fromkeys(span for region in sheet.regions for span in region.merged_ranges)),
    ) for sheet in summary.sheets)
    source = WorkbookSource(index.source_digest, sheets, content, limits or SourceReadLimits())
    return replace(index, source_provider=source)
