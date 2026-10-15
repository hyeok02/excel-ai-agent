"""Find missing formulas only in the requested sources, not anywhere in a file."""
import re

from app.agent.query.metric_observation_cells import metric_label_matches
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_scope import explicit_ranges, request_matches_plan, _inside
from app.agent.query.tabular_validation import query_columns


def explicit_formula_refs(question, sources):
    sheets = {row.sheet_name for row in sources.original_index.rows}
    ranges = []
    for sheet in sheets:
        names = [re.escape(sheet), re.escape("'" + sheet.replace("'", "''") + "'")]
        pattern = rf"(?:{'|'.join(names)})!\$?([A-Za-z]{{1,3}}\$?[1-9]\d*(?::\$?[A-Za-z]{{1,3}}\$?[1-9]\d*)?)"
        ranges.extend((sheet, address.upper().replace("$", "")) for address in re.findall(pattern, question, re.I))
    if not ranges and "!" not in question and re.search(r"셀|cell|값|value", question, re.I):
        names = [name for name in sheets if re.search(rf"(?<!\w){re.escape(name)}(?!\w)", question, re.I)]
        names = names or (list(sheets) if len(sheets) == 1 else [])
        if len(names) == 1:
            ranges = [(names[0], address.upper().replace("$", "")) for address in
                      re.findall(r"(?<![A-Za-z0-9_])\$?[A-Za-z]{1,3}\$?[1-9]\d*(?![A-Za-z0-9_])", question)]
    return [reference for reference in sources.resolutions if any(
        reference.rsplit("!", 1)[0].casefold() == sheet.casefold()
        and _inside(reference.rsplit("!", 1)[1], address) for sheet, address in ranges)]


def relevant_missing_formulas(question, sources, intent=None):
    unresolved = {key: item for key, item in sources.resolutions.items() if item.status == "unavailable"}
    explicit = explicit_formula_refs(question, sources)
    if explicit:
        return [unresolved[key] for key in explicit if key in unresolved]
    if not unresolved or (intent and intent.kind in {"summary", "brief", "structure", "formula_risk"}):
        return []
    query = getattr(intent, "tabular_query", None)
    if query is not None:
        tables = build_query_tables(sources.summary)
        table = next((table for table in tables if table.id == query.table_id), None)
        plan = bind_tabular_plan(query, table) if table else None
        if plan and request_matches_plan(question, plan, table, tables, intent):
            needed = set(query_columns(plan, table) or []) | {item.column_id for item in plan.filters}
            if plan.order_by:
                needed.add(plan.order_by)
            return [unresolved[key] for row in table.rows for column in needed
                    if (key := f"{table.sheet_name}!{column}{row.row_number}") in unresolved]
        return []
    # A named report metric on a horizontal row can explain why lookup failed.
    # It is deliberately not used to choose a period or manufacture a value.
    found = []
    names = {row.sheet_name for row in sources.original_index.rows
             if row.sheet_name.casefold() in question.casefold()}
    for row in sources.original_index.rows:
        if names and row.sheet_name not in names:
            continue
        if any(isinstance(cell.value, str) and metric_label_matches(cell.value, question)
               for cell in row.cells):
            found.extend(unresolved[cell.reference] for cell in row.cells if cell.reference in unresolved)
    return found
