"""Bind exact source labels as well as catalog IDs; never guess fuzzy matches."""
from app.agent.query.ambiguity_labels import resolve_unique_column


def bind_tabular_plan(plan, table):
    def resolve(value):
        matched = resolve_unique_column(value, table)
        if matched is None:
            raise ValueError("Missing or ambiguous source column")
        return matched

    try:
        return plan.model_copy(update={
            "column_ids": [resolve(value) for value in plan.column_ids],
            "group_by": [resolve(value) for value in plan.group_by],
            "identity_column_ids": [resolve(value) for value in plan.identity_column_ids],
            "filters": [condition.model_copy(update={"column_id": resolve(condition.column_id)})
                        for condition in plan.filters],
            "having": [condition.model_copy(update={"column_id": resolve(condition.column_id)
                        if condition.column_id else None}) for condition in plan.having],
            "order_by": resolve(plan.order_by) if plan.order_by else None,
        })
    except ValueError:
        return None
