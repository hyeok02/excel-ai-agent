"""Checks of a GPT calculation plan against the question, before it is run.

A plan can vary between runs; one that leaves out a value the question names as written
("부산 창고 재고 비중" computed over every warehouse alone) is sent back once with the reason.
"""
from app.agent.query.gpt_calc_planner import column_name
from app.agent.query.tabular_request_categories import value_matches

MAX_DISTINCT = 60


def unused_values(question, table, calc):
    """Source values written in the question that the plan neither filters on nor groups by."""
    grouped = {" ".join(name.split()).casefold() for name in calc.group_by}
    used = {item.value.strip().casefold() for item in calc.filters}
    missing = []
    for column in table.columns:
        values = {value.strip() for row in table.rows if isinstance(value := row.values.get(column.id), str)
                  and value.strip()}
        if not 2 <= len(values) <= MAX_DISTINCT or {column_name(column).casefold(), column.id.casefold()} & grouped:
            continue
        missing += [value for value in values if len(value) >= 2 and value.casefold() not in used
                    and value_matches(question, value)]
    return sorted(set(missing))
