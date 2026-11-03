"""Select an adjacent distinct aggregate rank from a fully read group population."""
from app.agent.query.grouped_aggregate_postprocess import aggregate_value

MAX_RELATIVE_TIES = 100


def relative_plan_valid(plan):
    anchor = plan.relative_rank
    if anchor is None:
        return True
    if (plan.group_by != [anchor.column_id] or plan.limit != 1 or plan.having
            or plan.share_of_total or plan.per_group_limit is not None
            or plan.filter_expression is not None
            or any(item.column_id == anchor.column_id for item in plan.filters)):
        return False
    if plan.operation in {"row_count", "distinct_count"}:
        return plan.order_by is None
    return (plan.operation == "numeric_summary" and len(plan.column_ids) == 1
            and plan.order_by == plan.column_ids[0] and plan.statistic != "all")


def select_relative_groups(plan, state, groups):
    """None means missing/ambiguous anchor, unknown measure or excessive ties."""
    from app.agent.query.grouped_tabular_state import typed_key
    anchor = plan.relative_rank
    original = anchor._original_request_label
    if original and _label_key(original) != _label_key(str(anchor.value)):
        if any(len(identity[0]) > 1 and _label_key(str(identity[0][1])) == _label_key(original)
               for identity in state.groups):
            return None  # A real original-language source identity outranks a translated alias.
    matches = []
    spellings = {}
    for identity, group in state.groups.items():
        key = identity[0]
        if len(key) > 1:
            spellings[id(group)] = _label_key(str(key[1]))
        expected = typed_key(anchor.value, "General")
        same = expected is not None and key[:2] == expected[0][:2]
        if key[0] == "text" and isinstance(anchor.value, str):
            same = _label_key(key[1]) == _label_key(anchor.value)
        if same:
            matches.append(group)
    if len(matches) != 1:
        return None
    anchored = matches[0]
    spoken = {_label_key(str(anchor.value)), spellings[id(anchored)]}
    if any(group_id != id(anchored) and spelling in spoken for group_id, spelling in spellings.items()):
        return None  # Equal spelling is not proof that text/numeric/boolean identities are interchangeable.
    key = lambda group: aggregate_value(plan, group, plan.order_by)
    reference = key(anchored)
    if reference is None or any(key(group) is None for group in groups):
        return None
    lower = plan.descending == (anchor.direction == "after")
    candidates = [group for group in groups if (key(group) < reference if lower else key(group) > reference)]
    if not candidates:
        return [], anchored, []
    target = (max if lower else min)(key(group) for group in candidates)
    selected = [group for group in candidates if key(group) == target]
    if len(selected) > MAX_RELATIVE_TIES:
        return None
    ties = sum(key(group) == reference for group in groups)
    notes = []
    if len(selected) > 1:
        notes.append(f"다음 순위가 동점이므로 {len(selected)}개 그룹을 모두 표시했습니다.")
    if ties > 1:
        notes.append(f"기준 항목과 같은 값의 {ties}개 그룹은 같은 순위로 보아 건너뛰었습니다.")
    return selected, anchored, notes


def _label_key(value):
    # Request spelling accepts case/spacing variants, so the entire population
    # must prove those variants identify exactly one group, even beyond samples.
    return " ".join(value.casefold().split())
