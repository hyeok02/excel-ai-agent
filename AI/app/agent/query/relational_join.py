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
    selected_keys = {_key(row, left_keys) for row in rows["left"]}
    lookup = {}
    for row in rows["right"]:
        key = _key(row, right_keys)
        # Cardinality is a property of the selected join population. An unused
        # duplicate dimension key cannot multiply these detail rows. Null keys
        # never match each other, including partially empty composite keys.
        if key is None or key not in selected_keys:
            continue
        if key in lookup:
            hint = _additional_key_hint(sides, rows, left_keys, right_keys)
            raise RelationalError("오른쪽 표의 연결 키가 중복되어 합계가 부풀 수 있습니다. 고유한 추가 키가 필요합니다." + hint)
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
    values = [row.values[column] for column in columns]
    typed = [None if value is None or (isinstance(value, str) and not value.strip())
             else _typed_value(value) for value in values]
    if None in typed:
        return None
    return tuple(typed)


def _additional_key_hint(sides, rows, left_keys, right_keys):
    candidates = []
    for right_column in sides["right"].columns:
        if right_column.id in right_keys:
            continue
        left_columns = [column for column in sides["left"].columns
                        if column.id not in left_keys and column.header.strip().casefold() == right_column.header.strip().casefold()]
        if len(left_columns) != 1:
            continue
        left_column = left_columns[0]
        try:
            selected = [_key(row, left_keys + [left_column.id]) for row in rows["left"]]
            keys = [_key(row, right_keys + [right_column.id]) for row in rows["right"]]
        except RelationalError:
            continue
        selected_set = set(selected)
        relevant = [key for key in keys if key is not None and key in selected_set]
        # A proposal must be usable for every selected source row and must
        # remove actual ambiguity. This is a suggestion, not inferred intent.
        if not selected or None in selected_set or not selected_set <= set(relevant) or len(relevant) != len(set(relevant)):
            continue
        candidates.append(f"{sides['left'].sheet_name}.{left_column.header} = {sides['right'].sheet_name}.{right_column.header}")
        if len(candidates) == 3:
            break
    if not candidates:
        return ""
    return " 원본에서 중복을 구분할 수 있는 추가 키 후보: " + "; ".join(candidates) + ". 이 기준으로 연결할지 명시해 주세요. 자동 적용하지 않았습니다."


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
