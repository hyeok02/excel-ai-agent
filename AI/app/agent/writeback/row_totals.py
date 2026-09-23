"""같은 행에서 이 셀을 품고 있는 합계 셀을 찾는다.

합계가 수식이 아니라 값으로 박혀 있으면 수식 의존 추적에 걸리지 않는다.
합계는 대개 값이 큰 항목 몇 개의 합이므로 큰 열만 추려 조합을 훑고,
한 행에서 맞는 덧셈은 우연일 수 있어 다른 행에서 다시 확인한다.
"""
from itertools import combinations

MAX_CANDIDATES = 12
MAX_PARTS = 6
MIN_CONFIRMING_ROWS = 3
MIN_CONFIRMING_RATIO = 0.8


def integer(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    rounded = round(value)
    return rounded if abs(value - rounded) < 1e-6 else None


def _confirmed(rows, columns, total_column, target_column) -> bool:
    """값이 모두 있는 행 가운데 덧셈이 성립하는 비율로 판단한다."""
    eligible = confirming = 0
    for row in rows:
        total = integer(row.get(total_column))
        parts = [integer(row.get(column)) for column in columns]
        if total is None or any(part is None for part in parts):
            continue
        eligible += 1
        if sum(parts) == total:
            confirming += 1
    return (
        confirming >= MIN_CONFIRMING_ROWS
        and confirming >= eligible * MIN_CONFIRMING_RATIO
    )


def _candidate_columns(target_row: dict, target_column: str) -> list[str]:
    scored = [
        (integer(value), column)
        for column, value in target_row.items()
        if column != target_column and integer(value) not in (None, 0)
    ]
    scored.sort(reverse=True)
    return [column for _, column in scored[:MAX_CANDIDATES]]


def find_row_total(target_row: dict, other_rows: list[dict], target_column: str):
    """(합계 열, 합을 이루는 열들). 찾지 못하면 None."""
    target_value = integer(target_row.get(target_column))
    # 값이 0인 셀은 어떤 합에 넣어도 성립해 우연한 짝이 잡힌다.
    if not target_value:
        return None
    candidates = _candidate_columns(target_row, target_column)
    for total_column in candidates:
        remainder = integer(target_row[total_column]) - target_value
        if remainder <= 0:
            continue
        parts = [column for column in candidates if column != total_column]
        for size in range(1, MAX_PARTS + 1):
            for chosen in combinations(parts, size):
                if sum(integer(target_row[column]) for column in chosen) != remainder:
                    continue
                used = [*chosen, target_column]
                if _confirmed(other_rows, used, total_column, target_column):
                    return total_column, used
    return None
