"""Bind exact source labels as well as catalog IDs; never guess fuzzy matches."""


def bind_tabular_plan(plan, table):
    def resolve(value):
        matches = {column.id for column in table.columns
                   if value == column.id or value == column.header}
        if len(matches) != 1:
            raise ValueError("Missing or ambiguous source column")
        return matches.pop()

    try:
        return plan.model_copy(update={
            "column_ids": [resolve(value) for value in plan.column_ids],
            "identity_column_ids": [resolve(value) for value in plan.identity_column_ids],
            "filters": [condition.model_copy(update={"column_id": resolve(condition.column_id)})
                        for condition in plan.filters],
        })
    except ValueError:
        return None
