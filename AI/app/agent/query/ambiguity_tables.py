"""Detect repeated table fields using only workbook labels and source context."""
from collections import defaultdict
from functools import lru_cache
import re
from app.agent.query.ambiguity_labels import (
    label_base,
    mentioned_sources,
    normalize_label,
    source_mentioned,
    source_or_reading_mentioned,
)
from app.agent.query.ambiguity_qualifiers import explicit_column_ids, qualified_labels
from app.agent.query.metric_observation_cells import metric_label_matches
from app.agent.query.metric_semantics import column_metric_conflict
from app.agent.query.metric_observation_render import _metric_identity
from app.agent.query.metric_observation_periods import LATEST
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_scope import explicit_ranges, _inside
from app.agent.query.clarification_table_preview import table_choice
from app.agent.query.source_record_identity import record_identities


def table_candidates(question, summary, index):
    if summary is None:
        return []
    tables, contexts = scoped_tables(question, build_query_tables(summary))
    metric_question = question
    for context in contexts:
        metric_question = re.sub(re.escape(context), " ", metric_question, flags=re.I)
    groups = defaultdict(list)
    for table in tables:
        for column in table.columns:
            if column.id in table.hidden_columns:
                continue
            base = label_base(column.header)
            if (not column_metric_conflict(column, metric_question) and len(normalize_label(base)) >= 3
                    and (source_mentioned(base, question) or metric_label_matches(base, metric_question))):
                groups[field_identity(column)].append((table, column))
    longest = {key: values for key, values in groups.items()
               if not any(key != other and key in other for other in groups)}
    for matches in longest.values():
        matches = narrow_matches(question, matches)
        identities = {(table.id, column.id) for table, column in matches}
        if len(identities) > 1:
            return candidates_for(question, matches, index)
    return []


def field_identity(column):
    return _header_identity(column.header)


@lru_cache(maxsize=65536)
def _header_identity(header):
    return normalize_label(_metric_identity(label_base(header)))


def candidates_for(question, matches, index):
    cells = {cell.reference: cell for row in index.rows for cell in row.cells}
    previews = [preview for table, column in matches
                if (preview := table_choice(question, table, column, cells, index)) is not None]
    explicit = explicit_ranges(question) or mentioned_sources((table.sheet_name for table, _ in matches), question)
    if LATEST.search(question) and not explicit and any(available for _, available, _ in previews):
        previews = [preview for preview in previews if not preview[2]]
    return [candidate for candidate, _, _ in previews]


def scoped_tables(question, tables):
    """Apply only scopes the user named: sheet, A1 range or table caption."""
    tables = [table for table in tables if len(table.hidden_columns) < len(table.columns)]
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
    return tables, contexts


def narrow_matches(question, matches):
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
        identities = record_identities(table, question)
        scores[table.id] = (len(identities), headers)
    if scores:
        best = max(scores.values())
        matches = [(table, column) for table, column in matches if scores[table.id] == best]
    return matches
