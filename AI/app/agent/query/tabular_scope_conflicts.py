"""Refuse a one-table plan when another source table answers it just as well.

The question, not the classifier's table ID, must select the source. A rival is
a table that holds every field the plan reads, so the same plan could run there.
Rivals are narrowed with the same sheet/range/caption scopes and label, qualifier
and record-identity evidence as the pre-execution ambiguity guard.
"""
from app.agent.query.ambiguity_candidates import clarification_answer
from app.agent.query.ambiguity_tables import candidates_for, field_identity, narrow_matches, scoped_tables
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_validation import query_columns


def plan_scope_conflict(question, plan, table, tables, needed):
    """None: no rival. (): evidence selects another table. Else competing fields."""
    by_id = {column.id: column for column in table.columns}
    read = set(needed) | {item.column_id for item in getattr(plan, "having", ()) if item.column_id}
    seeds = [by_id[key] for key in sorted(read) if key in by_id and field_identity(by_id[key])]
    if not seeds:
        seeds = [column for column in table.columns
                 if column.id not in table.hidden_columns and field_identity(column)]
    if not seeds:
        return None
    counted = plan.operation == "row_count" and not read
    rivals = [item for item in tables if item.id != table.id
              and all(_fields(item, seed) for seed in seeds) and not _same_answer(table, item, seeds, counted)]
    if not rivals:
        return None
    scoped = {item.id for item in scoped_tables(question, tables)[0]}
    if table.id not in scoped:
        return None  # A named other scope is rejected by request_matches_plan.
    rivals = [item for item in rivals if item.id in scoped]
    if not rivals:
        return None
    surviving = {table.id, *(item.id for item in rivals)}
    narrowed = {}
    for seed in seeds:
        matches = [(table, seed), *((item, column) for item in rivals for column in _fields(item, seed))]
        narrowed[seed.id] = narrow_matches(question, matches)
        surviving &= {item.id for item, _ in narrowed[seed.id]}
    if table.id not in surviving:
        return ()
    if len(surviving) == 1:
        return None
    primary = next((by_id[key] for key in plan.column_ids if key in by_id), seeds[0])
    return tuple((item, column) for item, column in narrowed.get(primary.id, narrowed[seeds[0].id])
                 if item.id in surviving)


def scope_clarification(plan, summary, data_index, question):
    """Ask which source table is meant instead of returning a generic failure."""
    if plan is None or summary is None:
        return None
    tables = build_query_tables(summary)
    matches = [table for table in tables if table.id == plan.table_id]
    if len(matches) != 1 or (plan := bind_tabular_plan(plan, matches[0])) is None:
        return None
    table = matches[0]
    selected = query_columns(plan, table) or []
    conflict = plan_scope_conflict(question, plan, table, tables, needed_columns(plan, selected))
    if not conflict:
        return None
    return clarification_answer(question, candidates_for(question, conflict, data_index), summary, data_index)


def needed_columns(plan, selected):
    needed = set(selected) | set(plan.group_by) | {item.column_id for item in plan.filters}
    if plan.order_by:
        needed.add(plan.order_by)
    return needed


def _fields(table, seed):
    key = field_identity(seed)
    return [column for column in table.columns
            if column.id not in table.hidden_columns and field_identity(column) == key]


def _same_answer(table, rival, seeds, counted):
    """Identical copies give identical answers; asking which one adds nothing.
    An unfiltered row count depends only on how many rows each table has."""
    if not (table.complete and rival.complete) or len(table.rows) != len(rival.rows):
        return False
    return counted or all(any([row.values.get(seed.id) for row in table.rows]
                   == [row.values.get(column.id) for row in rival.rows]
                   for column in _fields(rival, seed)) for seed in seeds)
