"""One table per period sheet ('January', 'February', 'March' or '2023', '2024'), read as one table too.

"1분기 거래 건수" counts the rows of every month: the sheets' rows are stacked under the columns they share,
with a 시트 column naming each row's sheet, so one period is still a filter (시트 = January) on the stack.
"""
from app.agent.query.gpt_calc_planner import column_name
from app.agent.query.tabular_catalog_models import QueryColumn, QueryRow, QueryTable

SHEET = "시트"
_ROWS = 1_000_000  # a stacked row is numbered by its sheet's place, then its own row
RECORDS = 20  # rows a sheet holds when it keeps records (transactions), not a few items


def stacked_tables(tables):
    from app.services.insights.narratives.sheet_periods import _period
    largest = {}
    for table in tables:
        if _period(table.sheet_name) and table.columns and table.rows and (
                table.sheet_name not in largest or len(table.rows) > len(largest[table.sheet_name].rows)):
            largest[table.sheet_name] = table
    group = sorted(largest.values(), key=lambda table: _period(table.sheet_name))
    if len(group) < 2 or len({_period(table.sheet_name)[0] for table in group}) != 1 or any(
            len(table.rows) < RECORDS for table in group):
        return []  # a few items a sheet ('2023년': 4 products) are read cell by cell, sheet beside sheet
    named = [{column_name(column): column for column in table.columns} for table in group]
    shared = [name for name in named[0] if all(name in found for found in named[1:])]
    if len(shared) < 2 or any(len(shared) < 0.8 * len(found) for found in named):
        return []  # sheets of other columns are not the same records
    rows = []
    for place, (table, found) in enumerate(zip(group, named), 1):
        for row in table.rows:
            values = {named[0][name].id: row.values.get(found[name].id) for name in shared}
            formats = {named[0][name].id: row.number_formats.get(found[name].id) for name in shared
                       if row.number_formats.get(found[name].id)}
            rows.append(QueryRow(place * _ROWS + row.row_number, {**values, SHEET: table.sheet_name},
                                 number_formats=formats))
    sheets = [table.sheet_name for table in group]
    column = QueryColumn(id=SHEET, header=SHEET, header_reference="", sample_values=tuple(sheets))
    return [QueryTable(id="stacked:" + "|".join(sheets), sheet_name=" + ".join(sheets), reference=group[0].reference,
                       columns=(*(named[0][name] for name in shared), column), rows=tuple(rows), complete=True,
                       source_kind="stacked")]


def statement_and_period_tables(tables, index):
    """A statement's row names under an empty header cell, then month sheets read as one table first."""
    from app.agent.query.gpt_calc_pairs import pair_tables
    from app.agent.query.gpt_calc_statements import labeled_tables
    tables = labeled_tables(tables, index)
    return [*stacked_tables(tables), *tables, *pair_tables(tables, index)]  # values beside their names, last
