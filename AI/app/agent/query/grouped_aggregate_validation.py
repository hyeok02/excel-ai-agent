"""Reject ambiguous aggregate combinations before reading or certifying rows."""


def valid_aggregate_plan(plan, columns, measures):
    groups = plan.group_by
    if (plan.operation not in {"numeric_summary", "row_count", "distinct_count"}
            or plan.column_scope != "selected" or plan.per_group_limit is not None
            or len(set(groups)) != len(groups)
            or not set(groups + plan.column_ids) <= columns.keys()):
        return False
    if plan.operation == "distinct_count":
        if (not 1 <= len(plan.column_ids) <= 3
                or len(set(plan.column_ids)) != len(plan.column_ids)
                or plan.order_by is not None or plan.share_of_total
                or not groups and plan.limit is not None):
            return False
    elif not groups:
        return False
    elif plan.operation == "row_count":
        if plan.order_by is not None or not set(plan.column_ids) <= set(groups):
            return False
    elif (not measures or set(measures) & set(groups)
          or (plan.order_by or plan.limit is not None)
          and (plan.order_by not in measures or plan.statistic == "all")):
        return False
    if plan.share_of_total and (not groups or plan.operation == "numeric_summary"
                               and (len(measures) != 1 or plan.statistic != "sum")):
        return False
    for condition in plan.having:
        if condition.target == "share":
            if (not plan.share_of_total or condition.column_id is not None
                    or condition.value_unit != "percent"):
                return False
        elif plan.operation == "numeric_summary":
            if condition.column_id not in measures or plan.statistic == "all":
                return False
        elif condition.column_id is not None or condition.value_unit != "raw":
            return False
    return True
