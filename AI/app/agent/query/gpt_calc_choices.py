"""Ask-backs that the question itself settles, handed to the GPT-chosen calculation instead.

- The same column on period sheets ('January'!…, 'February'!…): the sheets stacked answer it.
- Cells along one row or one column ('Summary'!B13 … F13): "가장 컸던 해" spans them, it does not pick one.
- Tables of different columns (Budget's Income vs the Expenses list): which one the question means is read
  from their names, unlike copies of one layout ('all trusts' · 'type 1 trusts') or one table's columns.
"""
import re

from openpyxl.utils.cell import coordinate_from_string

_CELL = re.compile(r"^\$?[A-Z]{1,3}\$?\d+$")


def unneeded_choice(answer, summary=None):
    from app.services.insights.narratives.sheet_periods import _period
    scopes = [_split(option.scope) for option in answer.clarification_options if "!" in option.scope]
    sheets = {sheet for sheet, _ in scopes}
    if len(scopes) < 2:
        return False
    if len(sheets) >= 2 and all(_period(sheet) for sheet in sheets):
        return True
    if len(sheets) == 1 and all(_CELL.match(cells) for _, cells in scopes):
        places = [coordinate_from_string(cells.replace("$", "")) for _, cells in scopes]
        return len({column for column, _ in places}) == 1 or len({row for _, row in places}) == 1
    return len(set(scopes)) == len(scopes) and summary is not None and _different_tables(scopes, summary)


def _split(scope):
    sheet, cells = scope.rsplit("!", 1)
    return " ".join(sheet.strip("'").split()), cells.strip()


def _different_tables(scopes, summary):
    from app.agent.query.gpt_calc_planner import column_name
    from app.agent.query.tabular_catalog import build_query_tables
    tables = {(" ".join(table.sheet_name.split()), table.reference): table for table in build_query_tables(summary)}
    headers = []
    for scope in scopes:
        if (table := tables.get(scope)) is None:
            return False
        headers.append({column_name(column).casefold() for column in table.columns})
    return all(len(a & b) < 0.5 * len(a | b) for number, a in enumerate(headers) for b in headers[number + 1:])
