"""다른 시트가 같은 값을 따로 들고 있는 셀을 찾는다.

수식으로 연결돼 있지 않으면 한쪽만 고쳤을 때 두 시트의 값이 어긋난다.
열 머리글이 같고 이어지는 값들이 그대로 겹칠 때만 복제로 본다.
"""
HEADER_LOOKUP_ROWS = 6
SERIES_LENGTH = 12
MIN_MATCHED_VALUES = 5
MAX_HEADER_OFFSET = 4
MAX_MIRRORS = 3


def column_label(column: dict[int, object], row_number: int) -> str | None:
    """대상 셀 바로 위에서 가장 가까운 글자 머리글."""
    for step in range(1, HEADER_LOOKUP_ROWS + 1):
        value = column.get(row_number - step)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _series(column: dict[int, object], start: int) -> list[object]:
    return [column.get(start + step) for step in range(SERIES_LENGTH)]


def _matched(left: list[object], right: list[object]) -> int:
    """앞에서부터 값이 겹치는 개수. 하나라도 어긋나면 0."""
    matched = 0
    for first, second in zip(left, right):
        if first is None or second is None:
            break
        if first != second:
            return 0
        matched += 1
    return matched


def find_mirrors(target_column, target_row: int, label: str, sheets) -> list[tuple]:
    """(시트, 열, 행) 목록. sheets는 {시트: {열: {행: 값}}} 형태."""
    source = _series(target_column, target_row)
    if sum(value is not None for value in source) < MIN_MATCHED_VALUES:
        return []
    found = []
    for sheet_name, columns in sheets.items():
        for letter, column in columns.items():
            for header_row, header in column.items():
                if not isinstance(header, str) or header.strip() != label:
                    continue
                for offset in range(1, MAX_HEADER_OFFSET + 1):
                    if _matched(source, _series(column, header_row + offset)) >= MIN_MATCHED_VALUES:
                        found.append((sheet_name, letter, header_row + offset))
                        break
                if len(found) >= MAX_MIRRORS:
                    return found
    return found
