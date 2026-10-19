"""Prevent unsupported plan fields from falling through to a simpler answer."""


def has_bounded_features(plan):
    return bool(plan.group_by or plan.operation == "distinct_count" or plan.having
                or plan.share_of_total or plan.per_group_limit is not None
                or plan.operation == "row_list" and plan.order_by)


def feature_contract_matches(plan, table):
    columns = {column.id for column in table.columns}
    if plan.per_group_limit is not None or plan.operation == "row_list" and plan.group_by:
        return (plan.operation == "row_list" and plan.column_scope == "selected"
                and 1 <= len(plan.group_by) <= 3 and len(set(plan.group_by)) == len(plan.group_by)
                and plan.per_group_limit is not None and plan.limit is None
                and plan.order_by in columns and plan.order_by not in plan.group_by
                and bool(plan.column_ids) and not plan.having and not plan.share_of_total
                and set(plan.group_by + plan.column_ids) <= columns
                and len(plan.identity_column_ids) <= 3
                and len(set(plan.identity_column_ids)) == len(plan.identity_column_ids)
                and not set(plan.identity_column_ids) & set(plan.group_by + [plan.order_by])
                and set(plan.identity_column_ids) <= set(plan.column_ids))
    if plan.operation == "distinct_count" or plan.having or plan.share_of_total:
        from app.agent.query.grouped_aggregate_validation import valid_aggregate_plan
        return valid_aggregate_plan(plan, {column.id: column for column in table.columns},
                                    list(dict.fromkeys(plan.column_ids)))
    return True
