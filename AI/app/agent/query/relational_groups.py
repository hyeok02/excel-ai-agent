"""Preserve unresolved group membership explicitly rather than drop source rows."""
from collections import defaultdict

from app.agent.query.tabular_results import _display_cell


def partition_join_groups(plan, joined):
    groups, unresolved = defaultdict(list), 0
    for item in joined:
        keys, missing = [], False
        for reference in plan.group_by:
            side, column = reference.split(".")
            row = getattr(item, side)
            value = row.values[column] if row is not None else None
            if row is None:
                keys.append(("unmatched", None, "연결 안 됨 (그룹 미확정)"))
                missing = True
            elif value is None or (isinstance(value, str) and not value.strip()):
                keys.append(("blank", None, "원본 그룹 값 비어 있음"))
                missing = True
            else:
                keys.append((type(value).__name__, value, _display_cell(value, row.number_formats.get(column, "General"))))
        unresolved += missing
        groups[tuple(keys)].append(item)
    limitations = []
    if unresolved:
        limitations.append(f"그룹을 확정하지 못한 왼쪽 행 {unresolved}개는 미확정 그룹으로 별도 표시했습니다. "
                           "해당 행을 전체 결과에서 누락하거나 그룹 값을 추정하지 않았습니다.")
    return groups, limitations
