"""Re-derive a table-scope option from the table its follow-up question names.

Options are identified by a digest of the source file, the original question and
the exact candidate (scope, label, preview cells). Rebuilding the candidate for
each column of the named table and comparing identifiers proves the option was
issued for this file and question, without calling any model.
"""
from hmac import compare_digest

from app.agent.query.clarification_options import source_clarification_options
from app.agent.query.clarification_table_preview import table_choice
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_scope import explicit_ranges


def named_table_option(question, selection, sources):
    summary, index = sources.summary, sources.index
    if summary is None or index is None:
        return None
    named = set(explicit_ranges(question))
    tables = [table for table in build_query_tables(summary)
              if any(sheet == table.sheet_name and reference == table.reference.rpartition("!")[2]
                     for sheet, reference in named)]
    if not tables:
        return None
    cells = {cell.reference: cell for row in index.rows for cell in row.cells}
    for table in tables:
        for column in table.columns:
            if column.id in table.hidden_columns:
                continue
            preview = table_choice(selection.source_question, table, column, cells, index)
            if preview is None:
                continue
            for option in source_clarification_options(selection.source_question, [preview[0]], summary, index):
                if compare_digest(option.id, selection.option_id) and option.question == question:
                    return option
    return None
