"""Resolve exact IDs/headers and validate complete source observations."""
from app.agent.query.relational_models import RelationalError
from app.agent.query.tabular_validation import validated_table


def bind_relational_plan(plan, tables, index):
    sides = {}
    for side in ("left", "right"):
        selected = [table for table in tables if table.id == getattr(plan, f"{side}_table_id")]
        if len(selected) != 1:
            raise RelationalError("연결할 원본 표를 하나로 확정하지 못했습니다.")
        sides[side] = selected[0]
    if sides["left"].id == sides["right"].id:
        raise RelationalError("같은 표를 두 번 연결하는 계획은 실행하지 않았습니다.")
    plan = plan.model_copy(deep=True)
    for key in plan.on:
        for side in sides:
            name = f"{side}_column_id"
            setattr(key, name, _column(getattr(key, name), sides[side]))
    if len({(key.left_column_id, key.right_column_id) for key in plan.on}) != len(plan.on):
        raise RelationalError("연결 키가 중복 지정되었습니다.")
    plan.column_ids = [_qualified(value, sides) for value in plan.column_ids]
    plan.group_by = [_qualified(value, sides) for value in plan.group_by]
    if plan.operation == "numeric_summary":
        # A model can include a grouping column in its projection as well as
        # group_by. It is already rendered as a group label, not a numeric
        # measure; never aggregate it or apply repeated-value checks to it.
        plan.column_ids = list(dict.fromkeys(ref for ref in plan.column_ids if ref not in plan.group_by))
    for condition in plan.filters:
        condition.column_id = _column(condition.column_id, sides[condition.side])
    needed = {side: {getattr(key, f"{side}_column_id") for key in plan.on} for side in sides}
    for reference in plan.column_ids + plan.group_by:
        side, column = reference.split(".")
        needed[side].add(column)
    for condition in plan.filters:
        needed[condition.side].add(condition.column_id)
    for side, table in sides.items():
        if table.excluded_rows:
            raise RelationalError("숨겨진 행이 제외된 표는 전체 연결 집계로 확정하지 않았습니다.")
        if not validated_table(table, index, needed[side]):
            raise RelationalError("연결 대상 표의 전체 행·수식 저장값을 원본과 대조하지 못했습니다.")
    return plan, sides, needed


def _column(value, table):
    exact = [column.id for column in table.columns if column.id == value]
    named = [column.id for column in table.columns if column.header.strip().casefold() == value.strip().casefold()]
    choices = exact or named
    if len(choices) != 1:
        raise RelationalError(f"‘{value}’ 열을 원본에서 하나로 확정하지 못했습니다.")
    return choices[0]


def _qualified(value, sides):
    side, separator, column = value.partition(".")
    if not separator or side not in sides:
        raise RelationalError("선택할 열의 원본 표가 구분되지 않았습니다.")
    return f"{side}.{_column(column, sides[side])}"
