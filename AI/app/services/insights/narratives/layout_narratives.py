"""Narratives that read a file's layout before its values: totals kept apart by a two-way column,
sheets of one layout named by their years, years over their parts, and tables side by side.

Each fires only on its layout; any other file gets ([], "") and is narrated as before.
"""
from app.services.insights.narratives.layout_tables import sheet_tables
from app.services.insights.narratives.period_columns import period_column_report
from app.services.insights.narratives.sheet_periods import sheet_period_report
from app.services.insights.narratives.side_tables import side_table_report
from app.services.insights.narratives.split_totals import split_report


def layout_report(context):
    for reporter in (sheet_period_report, side_table_report):
        items, overview = reporter(context)
        if items:
            return items, overview
    for sheet in context.get("sheets", []):
        for table in sheet_tables(sheet):
            for reporter in (period_column_report, split_report):
                found = reporter(table)
                if found:
                    return found
    return [], ""
