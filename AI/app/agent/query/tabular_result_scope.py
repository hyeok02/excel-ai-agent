"""Describe row filters, aggregate predicates and rank partitions separately."""
from app.agent.query.tabular_results import scope_description

_OPS = {"equals": "=", "not_equals": "≠", "greater_than": ">", "greater_than_or_equal": "≥",
        "less_than": "<", "less_than_or_equal": "≤"}


def result_scope(plan, table):
    if not plan.group_by and not plan.having and not plan.share_of_total:
        return scope_description(plan, table)
    columns = {column.id: column.header for column in table.columns}
    basic = plan.model_copy(update={"order_by": None, "limit": None})
    parts = []
    if plan.group_by:
        parts.append(", ".join(columns[key] for key in plan.group_by) + "별 "
                     + ("그룹 내 행 순위" if plan.per_group_limit is not None else "집계"))
    if plan.order_by or plan.limit:
        label = columns[plan.order_by] if plan.order_by else (
            "중복 제외 건수" if plan.operation == "distinct_count" else "행 개수")
        parts.append(f"{label} {'내림차순' if plan.descending else '오름차순'}")
    if plan.per_group_limit is not None:
        parts.append(f"각 그룹에서 앞의 {plan.per_group_limit}개 행")
    elif plan.limit:
        parts.append(f"앞의 {plan.limit}개 그룹")
    if plan.having:
        conditions = []
        for condition in plan.having:
            label = "전체 대비 비중" if condition.target == "share" else (
                columns[condition.column_id] if condition.column_id else "집계 건수")
            unit = "%" if condition.value_unit == "percent" else ""
            conditions.append(f"{label} {_OPS[condition.operator]} {condition.value:,}{unit}")
        parts.append("집계 후 조건: " + " 그리고 ".join(conditions))
    if plan.share_of_total:
        parts.append("행 필터를 통과한 전체 기준 비중(집계 후 조건·순위 제한 전 분모)")
    return scope_description(basic, table) + ", ".join(parts) + "\n"
