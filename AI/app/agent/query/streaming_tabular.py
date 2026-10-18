"""Execute a bounded plan against its entire original, authorized rectangle."""
from dataclasses import replace
import re

from openpyxl.utils import range_boundaries

from app.agent.query.streaming_tabular_boundaries import ambiguous_boundary
from app.agent.query.streaming_tabular_results import StreamResult, stream_answer
from app.agent.query.streaming_tabular_rows import header_matches, row_eligible, source_row, source_scope
from app.agent.query.streaming_tabular_witnesses import RequestWitnesses
from app.agent.query.tabular_request_constraints import _without_source_names
from app.agent.query.tabular_request_scope import request_matches_plan, rows_match_explicit_ranges
from app.agent.query.tabular_validation import query_columns


def execute_streaming_tabular(plan, table, tables, index, question, intent):
    from app.agent.query.workbook_source import source_for
    from app.agent.query.workbook_source_models import SourceReadError

    provider = source_for(index)
    if provider is None or plan.column_scope != "selected" or plan.order_by or plan.limit is not None:
        return None
    if re.search(r"(?:상위|하위|top|bottom)\s*\d+", _without_source_names(question, tables), re.I):
        return None
    selected = query_columns(plan, table)
    if selected is None or not selected and plan.operation != "row_count":
        return None
    filter_columns = {condition.column_id for condition in plan.filters}
    needed = set(selected) | filter_columns
    columns = {column.id: column for column in table.columns}
    if not needed <= columns.keys():
        return None
    try:
        sheet = source_scope(provider, index, table, needed, tables, question)
        if sheet is None:
            return None
        result = StreamResult(plan, [columns[column] for column in selected])
        witnesses = RequestWitnesses(question, plan)
        numeric_columns = set()
        left, top, right, bottom = range_boundaries(table.reference)
        expected = top
        scan = provider.scan_rows(table.sheet_name, table.reference)
        with scan as rows:
            for indexed in rows:
                if indexed.sheet_name != table.sheet_name or indexed.row_number != expected:
                    return None
                expected += 1
                if indexed.row_number == top:
                    if not header_matches(indexed, table):
                        return None
                    continue
                if indexed.row_number in sheet.hidden_rows:
                    result.hidden += 1
                    continue
                row = source_row(indexed, table)
                if not row.formulas and not any(value not in (None, "") for value in row.values.values()):
                    continue
                if ambiguous_boundary(row, table, numeric_columns):
                    return None
                if any(row.formulas.get(column) and row.values[column] is None for column in filter_columns):
                    return None
                result.population += 1
                if not witnesses.add(row):
                    return None
                accepted = row_eligible(row, plan, table)
                if accepted is None:
                    return None
                if accepted:
                    if any(row.formulas.get(column) and row.values[column] is None for column in selected):
                        return None
                    if not rows_match_explicit_ranges(question, table, selected or list(columns), [row]) or not result.add(row):
                        return None
        if not scan.complete or expected != bottom + 1:
            return None
        witnessed = replace(table, rows=tuple(witnesses.rows), complete=True)
        all_tables = [witnessed if candidate.id == table.id else candidate for candidate in tables]
        if not request_matches_plan(question, plan, witnessed, all_tables, intent):
            return None
        return stream_answer(question, table, needed, result)
    except (SourceReadError, ValueError, TypeError, ArithmeticError):
        return None
