"""Typed, bounded many-to-one joins with explicit unmatched-row accounting."""
import math
from dataclasses import dataclass
from decimal import Decimal

from app.agent.query.relational_models import RelationalError
from app.agent.query.tabular_filters import filtered_rows


@dataclass(frozen=True)
class JoinedRow:
    left: object
    right: object | None


def joined_rows(plan, sides):
    # Right predicates are applied before matching. Retaining all left rows is
    # still mandatory unless the user explicitly requested matched records only.
    rows = {}
    for side, table in sides.items():
        predicates = [condition for condition in plan.filters if condition.side == side]
        rows[side] = filtered_rows(table, predicates)
        if rows[side] is None:
            raise RelationalError("연결 조건에 비교할 수 없는 값이 있어 행을 임의로 제외하지 않았습니다.")
    right_keys = [key.right_column_id for key in plan.on]
    left_keys = [key.left_column_id for key in plan.on]
    lookup = {}
    for row in rows["right"]:
        key = _key(row, right_keys)
        if key in lookup:
            raise RelationalError("오른쪽 표의 연결 키가 중복되어 합계가 부풀 수 있습니다. 고유한 추가 키가 필요합니다.")
        lookup[key] = row
    result, unmatched = [], 0
    for row in rows["left"]:
        right = lookup.get(_key(row, left_keys))
        if right is None:
            unmatched += 1
        if right is not None or (plan.join_type == "left" and plan.population == "all_left"):
            result.append(JoinedRow(row, right))
    if unmatched and plan.join_type == "inner" and plan.population == "all_left":
        raise RelationalError(f"왼쪽 표 {unmatched}개 행의 연결 대상을 찾지 못해 전체 합계를 계산하지 않았습니다.")
    return result, unmatched, len(rows["left"])


def _key(row, columns):
    return tuple(_typed_value(row.values[column]) for column in columns)


def _typed_value(value):
    if value is None or value == "" or (isinstance(value, str) and not value.strip()):
        raise RelationalError("비어 있는 연결 키가 있어 같은 항목으로 묶지 않았습니다.")
    if isinstance(value, bool):
        return ("boolean", value)
    if isinstance(value, (int, float)):
        if not math.isfinite(value):
            raise RelationalError("연결 키에 유효하지 않은 숫자가 있습니다.")
        return ("number", Decimal(str(value)))
    if isinstance(value, str):
        if value.startswith(("#REF!", "#N/A", "#VALUE!", "#NAME?", "#DIV/0!")):
            raise RelationalError("오류 값은 연결 키로 사용할 수 없습니다.")
        # Codes are exact: numeric-looking text, case and leading zeros retain
        # their identity instead of accidentally matching another identifier.
        return ("text", value)
    raise RelationalError("지원하지 않는 연결 키 형식입니다.")
