"""Checks of a GPT calculation plan against the question, before it is run.

A plan can vary between runs; one that leaves out a value the question names as written
("부산 창고 재고 비중" computed over every warehouse alone) is sent back once with the reason.
"""
import re

from app.agent.query.gpt_calc_bounds import _column_values, inclusive, year_to_date
from app.agent.query.gpt_calc_cells import evaluate
from app.agent.query.gpt_calc_planner import column_name
from app.agent.query.gpt_calc_scope_checks import year_problem
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
        names = {column_name(column).casefold(), column.id.casefold()}
        narrowed = any(" ".join(item.column.split()).casefold() in names and item.op == "eq" for item in calc.filters)
        if not 2 <= len(values) <= MAX_DISTINCT or names & grouped and not narrowed:  # grouped, all its values kept
            continue
        missing += [value for value in values if len(value) >= 2 and value.casefold() not in used
                    and value_matches(question, value)]
    return sorted(set(missing))


def plan_problem(question, table, calc, headings=None):
    """Every reason a table plan cannot answer as written, told back to GPT once; else None."""
    problems = []
    from app.agent.query.ambiguity_labels import distinct_sheet_mentioned
    named = distinct_sheet_mentioned((headings or {}).values(), question)  # "2026년" names the 'Year 2026' section
    if named and not any(item.op == "under" for item in calc.filters):
        problems.append(f"The question names the section {sorted(named)} of group_rows, and rows of other sections "
                        "look alike (the same months each year): keep only its rows with a filter op under.")
    if unused := unused_values(question, table, calc):
        problems.append(f"The question names {unused} as written in the table, but the plan neither filters on "
                        "nor groups by them (a filter on that column keeps only the values it names). Use them when "
                        "the question means those rows; keep the plan when the word only appears inside another phrase. "
                        "Two values of one column compared or one taken from the other (one value's total minus another's) are that "
                        "column in group_by: both totals and their difference are shown.")
    if any(item.op.endswith("_column") and item.value.strip() == item.column.strip() for item in calc.filters):
        problems.append("A column compared with itself in its own row is never true. A value against the previous "
                        "period's is versus_previous over the date grouped by period; count those above 0 with having.")
    if calc.subtract and calc.subtract == calc.measure and not calc.row_formula:
        problems.append("subtract names the measure itself, which leaves 0. To compare two parts of one column "
                        "(one value's rows and another's), group_by the column holding the parts and leave subtract null.")
    if calc.aggregate == "ratio" and not calc.filters and not calc.denominator and not calc.group_by:
        problems.append("A ratio over all rows with no filter is 100%. For the share of rows holding a value "
                        "('Y', '예'), filter that value and leave measure null.")
    if calc.add and not calc.row_formula and (calc.measure is None or not calc.group_by) \
            and not set(calc.add) <= set(calc.across):  # a formula replaces add; across already totals each column
        problems.append("add totals several columns into one value per row of each group. For one row's values "
                        "across columns (a trend over year columns), use kind=cells with one item per column.")
    if calc.pick in {"above_mean", "below_mean"} and not calc.measure and not calc.row_formula and not calc.group_by:
        problems.append("above_mean compares each row's value with their mean: name the measure (the score) whose "
                        "rows above or below it are listed and counted.")
    if any(item.measure == calc.measure and item.aggregate == calc.aggregate and not item.row_formula for item in calc.also):
        problems.append("also repeats the main calculation over the same rows, so every line gives one number. For "
                        "several sheets together use the table whose sheet joins them with ' + ' (its 시트 column).")
    problems += filter(None, [year_problem(question, table, calc)])  # "2023년" over 2022 and 2023 rows
    return " ".join(problems) or None


def with_cell_values(calc, cells, question=""):
    """The plan with each "[Sheet!B66]" filter value replaced by that number cell's value, and bounds inclusive."""
    filters = []
    for item in map(lambda item: _column_values(inclusive(question, item), cells), calc.filters):
        if re.fullmatch(r"\s*\[[^\[\]]+![A-Za-z]{1,3}\d+\]\s*", item.value) and (found := evaluate(item.value, cells)):
            # "gt_column [Table!B66]": a cell, not a column of the row, so a plain comparison with its value
            item = item.model_copy(update={"value": repr(found[0]), "op": item.op.removesuffix("_column")})
        filters.append(item)
    calc = _settled(calc, year_to_date(question, filters))
    filters = calc.filters
    if calc.aggregate in {"max", "min"} and not calc.group_by and calc.pick == "all":  # "가장 큰 지출 한 건": the row
        return calc.model_copy(update={"filters": filters, "pick": "nth", "n": 1,
                                       "order": "desc" if calc.aggregate == "max" else "asc"})
    if calc.pick in {"top", "nth", "above_mean", "below_mean"} and not calc.group_by and calc.aggregate == "count" \
            and (calc.measure or calc.row_formula):  # rows ranked by their own score, not counted one by one
        calc = calc.model_copy(update={"aggregate": "sum"})
    if calc.pick in {"top", "nth"} and not calc.group_by and calc.aggregate in {"sum", "mean"} and (
            calc.then == "none" or calc.aggregate == "mean"):  # "상위 3일의 평균": the rows ranked, then their mean
        return calc.model_copy(update={"filters": filters, "then": calc.aggregate, "aggregate": "sum"})
    if calc.aggregate == "count_distinct" and not calc.measure and len(calc.group_by) == 1:
        # "몇 개 도시": the different values of the column grouped by, counted once over all rows
        return calc.model_copy(update={"filters": filters, "measure": calc.group_by[0], "group_by": []})
    return calc.model_copy(update={"filters": filters})


def _settled(calc, filters):
    """A plan made consistent with itself: what rank_of asks is ranked among all, a scope needs a part beside it,
    and 전월 대비 needs no column subtracted from itself."""
    if calc.rank_of:  # "선풍기는 몇 위": not ranked among 선풍기 alone
        filters = [item for item in filters if not (item.op == "eq" and " ".join(item.value.split()).casefold()
                                                    == " ".join(calc.rank_of.split()).casefold())]
    if calc.add and set(calc.add) <= set(calc.across) and not calc.group_by:  # each column totalled once, by across
        calc = calc.model_copy(update={"add": []})
    if calc.pick in {"above_mean", "below_mean"} and calc.group_by:  # the groups' mean is compared once, by the pick
        filters = [item for item in filters if item.value.strip().casefold() not in {"mean", "평균", "average"}]
    if filters and all(item.scope for item in filters):  # every filter a scope leaves no part: they pick the part
        filters = [item.model_copy(update={"scope": False}) for item in filters]
    update = {"filters": filters}
    if calc.versus_previous != "none" and calc.subtract == calc.measure:
        update["subtract"] = None
    return calc.model_copy(update=update)


def _names(calc):
    return {" ".join(str(name).split()).casefold() for name in [
        *calc.group_by, calc.measure, *re.split(r"\s*[,+]\s*", calc.denominator or ""), calc.subtract, calc.name_by,
        *calc.add, *calc.minus, *calc.across, *(item.measure for item in calc.also),
        *(item.column for item in calc.filters)] if name}


def _listed(table):
    return {column_name(column).casefold() for column in table.columns} | {column.id.casefold() for column in table.columns}


def unlisted_note(tables, index, calc):
    """What to tell GPT when its plan names no column of the table: which names, and that a row's value is a filter."""
    table = tables[index] if 0 <= index < len(tables) else None
    missing = sorted(_names(calc) - _listed(table)) if table is not None else []
    return (f"{missing} are not columns of table {index}. Name only its listed columns; a value written in a row "
            "(such as a row label) is a filter value, never a column." if missing else None)


def fitting_table(tables, index, calc):
    """The table the plan's column names belong to: the one it chose, else the only one that has them all."""
    names = _names(calc)
    def fits(table):
        return names <= _listed(table)
    if 0 <= index < len(tables) and fits(tables[index]):
        return tables[index]
    found = [table for table in tables if fits(table)]
    return found[0] if len(found) == 1 else None  # a wrong table number, read from the names it uses


def listed_cells(tables, cells):
    """The cells kind=cells may cite: not those of a table too long for its rows to be shown, which would be guesses."""
    from app.agent.query.gpt_calc_planner import SMALL_TABLE
    from app.agent.query.references import normalize_reference
    unseen = {normalize_reference(f"'{table.sheet_name}'!{column.id}{row.row_number}") for table in tables
              if len(table.rows) > SMALL_TABLE for row in table.rows for column in table.columns}
    return {reference: cell for reference, cell in cells.items() if reference not in unseen}
