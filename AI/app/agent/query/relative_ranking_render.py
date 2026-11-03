"""Lead with the computed adjacent rank; retain detailed source proof below it."""
from decimal import localcontext

from app.agent.query.grouped_aggregate_postprocess import aggregate_value
from app.agent.query.tabular_numeric import _render


def relative_rank_summary(plan, state, selected, anchor):
    names = {id(group): _name(identity[0]) for identity, group in state.groups.items()}
    direction = "다음" if plan.relative_rank.direction == "after" else "이전"
    subject = f"{names[id(anchor)]} {direction} 순위"
    if not selected:
        return subject + "의 그룹은 없습니다."
    winners = ", ".join(names[id(group)] for group in selected)
    value = aggregate_value(plan, selected[0], plan.order_by)
    if plan.operation == "numeric_summary":
        statistic = {"sum": "합계", "average": "평균", "min": "최솟값", "max": "최댓값"}[plan.statistic]
        metric = state.columns[plan.order_by].display_header + " " + statistic
        with localcontext() as context:
            context.prec = max(28, len(value.as_tuple().digits) + abs(value.as_tuple().exponent) + 10)
            amount = _render(value, selected[0].numeric[plan.order_by].spec)
    else:
        metric = "중복 제외 개수" if plan.operation == "distinct_count" else "행 개수"
        amount = f"{int(value):,}건"
    tie = " (공동 순위)" if len(selected) > 1 else ""
    each = "각각 " if len(selected) > 1 else ""
    return f"{subject}는 {winners}이며, {metric}는 {each}{amount}입니다{tie}."


def _name(identity):
    if identity[0] == "blank":
        return "빈칸 그룹"
    value = " ".join(str(identity[1]).split())
    kind = {"number": "숫자", "boolean": "논리값"}.get(identity[0])
    return f"{value} ({kind})" if kind else value
