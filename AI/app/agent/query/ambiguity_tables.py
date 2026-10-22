"""Detect repeated table fields using only workbook labels and source context."""
from collections import defaultdict
import re
from openpyxl.utils.cell import quote_sheetname

from app.agent.query.ambiguity_candidates import AmbiguousCandidate
from app.agent.query.ambiguity_labels import (
    label_base,
    mentioned_sources,
    normalize_label,
    source_mentioned,
    source_or_reading_mentioned,
)
from app.agent.query.ambiguity_qualifiers import explicit_column_ids, qualified_labels
from app.agent.query.metric_observation_cells import metric_label_matches
from app.agent.query.metric_observation_render import _metric_identity
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_scope import explicit_ranges, _inside


def table_candidates(question, summary, index):
    if summary is None:
        return []
    tables = [table for table in build_query_tables(summary)
              if len(table.hidden_columns) < len(table.columns)]
    named = mentioned_sources((table.sheet_name for table in tables), question)
    if named:
        tables = [table for table in tables if table.sheet_name in named]
    ranges = explicit_ranges(question)
    if ranges:
        tables = [table for table in tables if any(sheet == table.sheet_name
                  and _inside(reference, table.reference) for sheet, reference in ranges)]
    contexts = mentioned_sources((text for table in tables for _, text in table.context
                                  if len(normalize_label(text)) >= 4), question)
    if contexts:
        tables = [table for table in tables if contexts <= {text for _, text in table.context}]
    metric_question = question
    for context in contexts:
        metric_question = re.sub(re.escape(context), " ", metric_question, flags=re.I)
    groups = defaultdict(list)
    for table in tables:
        for column in table.columns:
            if column.id in table.hidden_columns:
                continue
            base = label_base(column.header)
            if len(normalize_label(base)) >= 3 and (source_mentioned(base, question)
                                                    or metric_label_matches(base, metric_question)):
                groups[normalize_label(_metric_identity(base))].append((table, column))
    longest = {key: values for key, values in groups.items()
               if not any(key != other and key in other for other in groups)}
    for matches in longest.values():
        matches = _narrow_matches(question, matches)
        identities = {(table.id, column.id) for table, column in matches}
        if len(identities) > 1:
            cells = {cell.reference: cell for row in index.rows for cell in row.cells}
            return [_candidate(question, table, column, cells) for table, column in matches]
    return []


def _narrow_matches(question, matches):
    if len(matches) < 2:
        return matches
    named_columns = explicit_column_ids(question)
    if named_columns:
        matches = [(table, column) for table, column in matches if column.id in named_columns]
    literal = [(table, column) for table, column in matches
               if source_mentioned(label_base(column.header), question)]
    if literal and len({normalize_label(label_base(column.header)) for _, column in matches}) > 1:
        # Explicit "Total Debt" must outrank a broad translated debt/liability
        # alias, but an unqualified "Revenue" cannot choose USD over EUR.
        matches = literal
    exact = [(table, column) for table, column in matches
             if normalize_label(column.header) != normalize_label(label_base(column.header))
             and source_mentioned(column.header, question)]
    if exact:
        matches = exact
    qualified = qualified_labels(question, [column.header for _, column in matches])
    matches = [(table, column) for table, column in matches if column.header in qualified]
    # Another explicitly named source field or record identity can select the
    # proper parallel table without trusting the classifier's chosen table ID.
    scores = {}
    for table, _ in matches:
        if table.id in scores:
            continue
        headers = sum(source_or_reading_mentioned(column.header, question) for column in table.columns
                      if column.id not in table.hidden_columns)
        identities = {str(value) for row in table.rows for value in row.values.values()
                      if isinstance(value, str) and 3 <= len(value.strip()) <= 100
                      and source_or_reading_mentioned(value, question)}
        scores[table.id] = (len(identities), headers)
    if scores:
        best = max(scores.values())
        matches = [(table, column) for table, column in matches if scores[table.id] == best]
    return matches



def _candidate(question, table, column, cells):
    context = " / ".join(text for _, text in table.context)[-160:]
    formats = ", ".join(value for value in column.number_formats if value != "General")
    details = "; ".join(value for value in (column.header_reference, context,
                          f"표시 형식: {formats}" if formats else "") if value)
    header = cells.get(column.header_reference)
    return AmbiguousCandidate(
        column.header, f"{quote_sheetname(table.sheet_name)}!{table.reference}", details or "단위·기간은 표에서 선택",
        f"{quote_sheetname(table.sheet_name)}!{table.reference} 범위의 {column.id}열 {column.header} 기준으로: {question}",
        (header,) if header else (),
    )
