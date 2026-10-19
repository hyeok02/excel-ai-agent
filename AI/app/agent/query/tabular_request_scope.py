"""Reject plans that contradict explicitly named source scopes and operations.

Natural-language interpretation chooses source IDs, never answer numbers. These
checks keep an otherwise valid computation from silently answering another field,
sheet or identifier. Source labels come from the workbook, not a business glossary.
"""
import re

from openpyxl.utils import range_boundaries
from app.agent.query.ambiguity_labels import label_base, mentioned_sources, source_mentioned
from app.agent.query.ambiguity_qualifiers import explicit_column_ids, qualified_labels, requested_units_match
from app.agent.query.metric_observation_cells import metric_label_matches
from app.agent.query.tabular_request_constraints import matches_constraints
from app.agent.query.tabular_request_categories import value_matches
from app.agent.query.tabular_having_language import without_checked_having


def request_matches_plan(question, plan, table, tables, intent=None, *, streaming=False):
    if intent is not None:
        allowed = {
            "lookup": {"cell_lookup"}, "row_list": {"row_list"},
            "row_count": {"row_count", "aggregation"},
            "distinct_count": {"row_count", "aggregation"},
            "numeric_summary": {"aggregation"},
            "frequencies": {"aggregation", "summary", "row_count"},
        }
        if intent.kind not in allowed[plan.operation]:
            return False
    text = _normal(question)
    named_sheets = mentioned_sources((item.sheet_name for item in tables), question)
    if named_sheets and table.sheet_name not in named_sheets:
        return False
    contexts = {_normal(value) for value in mentioned_sources(
        (value for candidate in tables for _, value in candidate.context if len(_normal(value)) >= 4), question)}
    selected_context = {_normal(value) for _, value in table.context}
    if contexts and not contexts <= selected_context:
        return False
    for sheet, reference in explicit_ranges(question):
        if sheet != table.sheet_name or not _inside(reference, table.reference):
            return False
    involved = set(plan.column_ids) | set(plan.group_by) | {item.column_id for item in plan.filters}
    involved.update(item.column_id for item in getattr(plan, "having", ()) if item.column_id)
    if plan.order_by:
        involved.add(plan.order_by)
    if plan.column_scope == "all_attributes":
        involved.update(column.id for column in table.columns)
    if not explicit_column_ids(question) <= involved:
        return False
    if plan.operation in {"numeric_summary", "lookup", "row_list"}:
        units_text = without_checked_having(question, plan, table) if getattr(plan, "having", ()) else question
        if units_text is None or not requested_units_match(units_text, [column.header for column in table.columns
                                               if column.id in plan.column_ids
                                               and (plan.operation == "numeric_summary"
                                                    or label_base(column.header) != column.header)]):
            return False
    if plan.operation == "numeric_summary":
        # Translated metric names constrain source fields, not just valid values.
        metric_question = question
        for caption in contexts:
            metric_question = re.sub(re.escape(caption), " ", metric_question, flags=re.I)
        metric_question = re.sub(
            r"(?:상위|하위|top|bottom)\s*\d+|최대|최소|\b(?:maximum|minimum|highest|lowest)\b",
            " ", metric_question, flags=re.I,
        )
        semantic_headers = {column.header for candidate in tables for column in candidate.columns
                            if (not named_sheets or candidate.sheet_name in named_sheets)
                            and (not contexts or contexts <= {_normal(value) for _, value in candidate.context})
                            and (metric_label_matches(column.header, metric_question)
                                 or source_mentioned(label_base(column.header), metric_question))}
        semantic_headers = qualified_labels(metric_question, semantic_headers)
        selected_headers = {column.header for column in table.columns
                            if column.id in involved and column.id not in plan.group_by}
        semantic_headers -= {column.header for column in table.columns if column.id in plan.group_by}
        if semantic_headers and not semantic_headers <= selected_headers:
            return False
    # Prefer longest explicit labels: "Amount" must not overrule "Net Amount".
    header_text = header_request_text(question, named_sheets)
    candidates = [(item, column) for item in tables
                  if not named_sheets or item.sheet_name in named_sheets
                  for column in item.columns
                  if len(_normal(column.header)) >= 4 and _normal(column.header) in header_text]
    candidates = [(item, column) for item, column in candidates
                  if not any(_normal(column.header) != _normal(other.header)
                             and _normal(column.header) in _normal(other.header)
                             for _, other in candidates)]
    for _, column in candidates:
        if not any(_normal(selected.header) == _normal(column.header)
                   and selected.id in involved for selected in table.columns):
            return False
    # A textual transaction/record ID in the question must be used as a filter;
    # finding the ID somewhere in the workbook is not sufficient.
    identifier_pattern = r"(?<![A-Za-z0-9_])(?:[A-Za-z]+[-_]?[0-9]+|#[A-Za-z0-9]+)(?![A-Za-z0-9_])"
    identifiers = re.findall(identifier_pattern, question)
    source_headers = {_normal(column.header) for candidate in tables for column in candidate.columns}
    source_scope_ids = {_normal(token) for label in named_sheets | contexts
                        for token in re.findall(identifier_pattern, label)}
    range_addresses = {address.casefold() for _, reference in explicit_ranges(question)
                       for address in reference.split(":")}
    identifiers = [identifier for identifier in identifiers
                   if _normal(identifier) not in source_headers
                   and _normal(identifier) not in source_scope_ids
                   and identifier.casefold() not in range_addresses]
    filters = {str(item.value).casefold() for item in plan.filters
               if item.operator == "equals"}
    # Keep the full source value as the identity when the request contains a
    # compound key (for example "Unit #21"), not just its regex ID fragment.
    source_values = {str(value).casefold() for row in table.rows for value in row.values.values()}
    bound_ids = {match.group().casefold() for value in filters & source_values
                 if value_matches(question, value)
                 for match in re.finditer(identifier_pattern, value)}
    if any(identifier.casefold() not in filters | bound_ids for identifier in identifiers):
        return False
    return matches_constraints(question, plan, table, tables, streaming=streaming)


def explicit_ranges(question):
    return [(quoted.replace("''", "'") if quoted else plain, first.upper() + (":" + last.upper() if last else ""))
            for quoted, plain, first, last in re.findall(
                r"(?:'((?:[^']|'')+)'|([\w& .-]+))!\$?([A-Za-z]{1,3}\$?[1-9]\d*)(?::\$?([A-Za-z]{1,3}\$?[1-9]\d*))?",
                question,
            )]


def rows_match_explicit_ranges(question, table, columns, rows):
    for _, reference in explicit_ranges(question):
        for row in rows:
            for column in columns:
                if not _inside(f"{column}{row.row_number}", reference):
                    return False
    return True


def _inside(inner, outer):
    a, b, c, d = range_boundaries(inner.replace("$", ""))
    e, f, g, h = range_boundaries(outer.replace("$", ""))
    return e <= a <= c <= g and f <= b <= d <= h


def _normal(value):
    return re.sub(r"\s+", " ", str(value).casefold()).strip()


def header_request_text(question, sheets):
    text = _normal(question)
    for sheet in sorted(sheets, key=len, reverse=True):
        for spelling in ("'" + sheet.replace("'", "''") + "'", sheet):
            text = re.sub(r"(?<!\w)" + re.escape(_normal(spelling))
                          + r"(?=\s*(?:시트|sheet\b|!))", " ", text, flags=re.I)
    return text
