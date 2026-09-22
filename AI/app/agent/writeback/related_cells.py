"""바꿀 셀과 함께 확인해야 할 셀을 찾는다.

수식으로 이어진 셀은 affected_cells가 잡는다. 여기서 찾는 것은 수식이 아니라
값으로 들어 있어 의존 추적에 걸리지 않는 셀이다. 같은 행의 합계와,
다른 시트가 따로 들고 있는 같은 값 두 가지를 본다.
"""
import re

from app.agent.writeback.mirrored_series import column_label, find_mirrors
from app.agent.writeback.models import WritebackRelatedCell
from app.agent.writeback.row_totals import find_row_total, integer

ADDRESS = re.compile(r"^([A-Z]{1,3})([1-9][0-9]*)$")
MAX_RELATED = 4


def sheet_columns(data_index) -> dict[str, dict[str, dict[int, object]]]:
    """{시트: {열: {행: 값}}}. 제안 한 건에서 한 번만 만든다."""
    sheets: dict[str, dict[str, dict[int, object]]] = {}
    for row in data_index.rows:
        for cell in row.cells:
            match = ADDRESS.match(cell.address.upper())
            if match is None or cell.value is None:
                continue
            column = sheets.setdefault(cell.sheet_name, {}).setdefault(match.group(1), {})
            column[int(match.group(2))] = cell.value
    return sheets


def _row_values(columns, row_number: int) -> dict[str, object]:
    return {
        letter: column[row_number]
        for letter, column in columns.items()
        if row_number in column
    }


def related_cells(sheets, sheet_name: str, reference: str, new_value) -> list:
    match = ADDRESS.match(reference.upper())
    columns = sheets.get(sheet_name)
    if match is None or columns is None or integer(new_value) is None:
        return []
    letter, row_number = match.group(1), int(match.group(2))
    found = _row_total(columns, sheet_name, letter, row_number, new_value)
    found += _mirrors(sheets, columns, sheet_name, letter, row_number, new_value)
    return found[:MAX_RELATED]


def _row_total(columns, sheet_name: str, letter: str, row_number: int, new_value) -> list:
    target = _row_values(columns, row_number)
    others = [
        _row_values(columns, number)
        for number in sorted(columns.get(letter, {}))
        if number != row_number
    ][:40]
    result = find_row_total(target, others, letter)
    if result is None:
        return []
    total_column, used = result
    before = integer(target[total_column])
    return [
        WritebackRelatedCell(
            sheet_name=sheet_name, reference=f"{total_column}{row_number}",
            current_value=before,
            suggested_value=before - integer(target[letter]) + integer(new_value),
            kind="total",
            reason=_total_reason(columns, total_column, letter, row_number, used),
        )
    ]


def _label(columns, letter: str, row_number: int) -> str:
    """열 머리글. 없으면 셀 주소를 그대로 쓴다."""
    return column_label(columns.get(letter, {}), row_number) or f"{letter}{row_number}"


def _total_reason(columns, total_column, letter, row_number, used) -> str:
    """열 문자 대신 사람이 읽는 머리글로 합계 관계를 설명한다."""
    total = _label(columns, total_column, row_number)
    target = _label(columns, letter, row_number)
    tail = (f"수식이 아니라 숫자로 적혀 있어, {target} 값만 바꾸면 합이 맞지 않습니다.")
    head = f"{total_column}{row_number}({total})은 이 행의 값 {len(used)}개를 더한 합계입니다"
    parts = ", ".join(sorted(_label(columns, name, row_number) for name in used))
    detailed = f"{head} — {parts}. {tail}"
    return detailed if len(detailed) <= 300 else f"{head}. {tail}"


def _mirrors(sheets, columns, sheet_name, letter, row_number, new_value) -> list:
    column = columns.get(letter, {})
    label = column_label(column, row_number)
    if label is None:
        return []
    others = {name: value for name, value in sheets.items() if name != sheet_name}
    found = []
    for mirror_sheet, mirror_letter, mirror_row in find_mirrors(
        column, row_number, label, others
    ):
        found.append(
            WritebackRelatedCell(
                sheet_name=mirror_sheet,
                reference=f"{mirror_letter}{mirror_row}",
                current_value=column.get(row_number),
                suggested_value=new_value,
                kind="mirror",
                reason=f"{mirror_sheet} 시트가 '{label}' 열에 같은 값을 따로 들고 있습니다. "
                       f"수식으로 연결돼 있지 않아 한쪽만 바꾸면 두 시트가 어긋납니다.",
            )
        )
    return found


def dedupe_related(changes: list) -> list:
    """이미 변경으로 제안한 셀은 관련 셀에서 뺀다. 화면에 두 번 나오지 않게."""
    proposed = {(change.sheet_name.casefold(), change.reference.upper()) for change in changes}
    for change in changes:
        change.related_cells = [
            cell
            for cell in change.related_cells
            if (cell.sheet_name.casefold(), cell.reference.upper()) not in proposed
        ]
    return changes
