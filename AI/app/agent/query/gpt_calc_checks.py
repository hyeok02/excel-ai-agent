"""Checks of a GPT calculation plan against the question, before it is run.

A plan can vary between runs; one that leaves out a value the question names as written
("부산 창고 재고 비중" computed over every warehouse alone) is sent back once with the reason.
"""
import re

from app.agent.query.gpt_calc_cells import evaluate
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


def plan_problem(question, table, calc):
    """Why a table plan cannot answer as written, told back to GPT once; else None."""
    if unused := unused_values(question, table, calc):
        return (f"The question names {unused} as written in the table, but the plan neither filters on "
                "nor groups by them: use them.")
    if calc.aggregate in {"max", "min"} and not calc.group_by:
        return ("A largest or smallest value without group_by names no winner. Group by the column naming the "
                "rows, or, when the things compared are column headers of one row, use kind=cells with one item "
                "per column and keep max or min.")
    if calc.aggregate == "ratio" and not calc.filters and not calc.denominator and not calc.group_by:
        return ("A ratio over all rows with no filter is 100%. For the share of rows holding a value ('Y', '예'), "
                "filter that value and leave measure null.")
    if calc.add and (calc.measure is None or not calc.group_by):
        return ("add totals several columns into one value per row of each group. For one row's values across "
                "columns (a trend over year columns), use kind=cells with one item per column.")
    return None


def with_cell_values(calc, cells):
    """The plan with each "[Sheet!B66]" filter value replaced by that number cell's value."""
    filters = []
    for item in calc.filters:
        if re.fullmatch(r"\s*\[[^\[\]]+![A-Za-z]{1,3}\d+\]\s*", item.value) and (found := evaluate(item.value, cells)):
            # "gt_column [Table!B66]": a cell, not a column of the row, so a plain comparison with its value
            item = item.model_copy(update={"value": repr(found[0]), "op": item.op.removesuffix("_column")})
        filters.append(item)
    if calc.aggregate == "count_distinct" and not calc.measure and len(calc.group_by) == 1:
        # "몇 개 도시": the different values of the column grouped by, counted once over all rows
        return calc.model_copy(update={"filters": filters, "measure": calc.group_by[0], "group_by": []})
    return calc.model_copy(update={"filters": filters})


def fitting_table(tables, index, calc):
    """The table the plan's column names belong to: the one it chose, else the only one that has them all."""
    names = {" ".join(str(name).split()).casefold() for name in [*calc.group_by, calc.measure, calc.denominator,
                                                                 calc.subtract, *calc.add, *(item.column for item in calc.filters)]
             if name}
    def fits(table):
        listed = {column_name(column).casefold() for column in table.columns} | {
            column.id.casefold() for column in table.columns}
        return names <= listed
    if 0 <= index < len(tables) and fits(tables[index]):
        return tables[index]
    found = [table for table in tables if fits(table)]
    return found[0] if len(found) == 1 else None  # a wrong table number, read from the names it uses
