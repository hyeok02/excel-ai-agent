"""A value asked of a small labelled table without naming its row: every row, labelled.

"2019년의 천식 유병률은?" on a table whose rows are Asthma Attack Prevalence and
Current Asthma Prevalence names a column but not a row. A lookup would have to
pick one of them, so it used to be refused. With a few rows that each carry a
distinct text label, each row's value is shown beside its own source label
instead: nothing is chosen for the user and no row is hidden.
"""
from app.agent.query.tabular_results import _display_cell, _identity_column

MAX_ROWS = 10


def label_column(plan, table, rows):
    """The text column naming each row, when an unscoped lookup should list them all."""
    if (plan.operation != "lookup" or plan.filters or getattr(plan, "filter_expression", None)
            or not 1 < len(rows) <= MAX_ROWS or len(table.rows) != len(rows)):
        return None
    column = _identity_column(table)
    if column is None or column in plan.column_ids:
        return None
    labels = [row.values.get(column) for row in rows]
    return column if all(isinstance(label, str) and label.strip() for label in labels) else None


def labelled_text(label, columns, rows):
    """One line per row: its source label, then each asked column's value as the source shows it."""
    lines = [f"표에서 행을 지정하지 않아 {len(rows)}개 항목을 모두 표시했습니다."]
    for row in rows:
        parts = []
        for column in columns:
            value = row.values[column.id]
            if value is None and row.formulas.get(column.id):
                return None
            parts.append(f"{column.display_header}: {_display_cell(value, row.number_formats.get(column.id, 'General'))}")
        lines.append(f"{row.values[label]} — {'; '.join(parts)}")
    return "\n".join(lines)
