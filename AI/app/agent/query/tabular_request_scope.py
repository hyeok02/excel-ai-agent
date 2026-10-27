"""Reject plans contradicting source scopes, metric meanings or operations."""
import re

from app.agent.query.ambiguity_labels import label_base, mentioned_sources, source_mentioned
from app.agent.query.ambiguity_qualifiers import explicit_column_ids, qualified_labels, requested_units_match
from app.agent.query.metric_observation_cells import metric_label_matches
from app.agent.query.metric_semantics import column_metric_conflict
from app.agent.query.tabular_request_constraints import matches_constraints
from app.agent.query.tabular_request_categories import value_matches
from app.agent.query.tabular_having_language import without_checked_having
from app.agent.query.tabular_population_context import unit_qualified_headers
from app.agent.query.tabular_header_paths import header_paths_match_request
from app.agent.query.tabular_explicit_scope import explicit_ranges, rows_match_explicit_ranges, _inside


def request_matches_plan(question, plan, table, tables, intent=None, *, streaming=False):
    if not header_paths_match_request(question, plan, table, tables):
        return False
    if any(column_metric_conflict(column, question) for column in table.columns if column.id in plan.column_ids):
        return False
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
    named_sheets = mentioned_sources((item.sheet_name for item in tables), question)
    if named_sheets and table.sheet_name not in named_sheets:
        return False
    contexts = {_normal(value) for value in mentioned_sources(
        (value for candidate in tables for _, value in candidate.context if len(_normal(value)) >= 4), question)}
    selected_context = {_normal(value) for _, value in table.context}
    if contexts and not contexts <= selected_context:
        return False
    for sheet, reference in explicit_ranges(question, include_unqualified=True):
        if (sheet and sheet != table.sheet_name) or not _inside(reference, table.reference):
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
        # A recognized sheet named "converter" or "환산" is a source scope,
        # not a request to convert the values. Conversion elsewhere remains.
        units_text = header_request_text(question, named_sheets)
        if getattr(plan, "having", ()):
            units_text = without_checked_having(units_text, plan, table)
        if units_text is None or not requested_units_match(units_text, unit_qualified_headers(plan, table, [column.display_header for column in table.columns
                                               if column.id in plan.column_ids
                                               and (plan.operation == "numeric_summary"
                                                    or label_base(column.display_header) != column.display_header)])):
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
    # A series identifier in a coordinate-bound metadata row identifies its
    # value column, unlike a transaction ID that must constrain a data row.
    series_ids = {_normal(value) for candidate in tables for column in candidate.columns
                  for _, value in getattr(column, "source_identifiers", ())}
    selected_series_ids = {_normal(value) for column in table.columns if column.id in involved
                           for _, value in getattr(column, "source_identifiers", ())}
    mentioned_series = {_normal(identifier) for identifier in identifiers} & series_ids
    if not mentioned_series <= selected_series_ids:
        return False
    range_addresses = {address.casefold().replace("$", "") for _, reference in explicit_ranges(question, include_unqualified=True)
                       for address in reference.split(":")}
    identifiers = [identifier for identifier in identifiers
                   if _normal(identifier) not in source_headers
                   and _normal(identifier) not in source_scope_ids
                   and _normal(identifier) not in selected_series_ids
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


def _normal(value):
    return re.sub(r"\s+", " ", str(value).casefold()).strip()


def header_request_text(question, sheets):
    text = _normal(question)
    for sheet in sorted(sheets, key=len, reverse=True):
        for spelling in ("'" + sheet.replace("'", "''") + "'", sheet):
            text = re.sub(r"(?<!\w)" + re.escape(_normal(spelling))
                          + r"(?=\s*(?:시트|sheet\b|!))", " ", text, flags=re.I)
    return text
