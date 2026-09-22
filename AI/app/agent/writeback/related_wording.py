"""관련 셀을 왜 함께 고쳐야 하는지 사람이 읽을 문장으로 만든다.

열 문자(AI, G, W …)는 읽는 사람에게 아무 뜻이 없어 열 머리글로 바꾸고,
더하는 값을 바꾸기 전후로 나란히 보여 준다.
"""
from app.agent.writeback.mirrored_series import column_label
from app.agent.writeback.row_totals import integer

MAX_REASON = 400


def label(columns, letter: str, row_number: int) -> str:
    """열 머리글. 없으면 셀 주소를 그대로 쓴다."""
    return column_label(columns.get(letter, {}), row_number) or f"{letter}{row_number}"


def _column_order(letter: str) -> tuple[int, str]:
    """엑셀 열 순서. 사전순으로 세우면 AI가 G보다 앞에 온다."""
    return len(letter), letter


def _sum_line(target, order, letter, new_value) -> str:
    parts = [integer(new_value if name == letter else target[name]) for name in order]
    return f"{' + '.join(str(part) for part in parts)} = {sum(parts)}"


def total_reason(columns, target, total, letter, row_number, used, new_value) -> str:
    others = sorted((name for name in used if name != letter), key=_column_order)
    order = [*others, letter]
    names = ", ".join(sorted(label(columns, name, row_number) for name in used))
    opening = f"{total}{row_number}({label(columns, total, row_number)})은 이 행의 "
    head = f"{opening}{names} {len(used)}가지를 더한 합계입니다."
    body = (
        f"\n지금: {_sum_line(target, order, letter, target[letter])}"
        f"\n바꾼 뒤: {_sum_line(target, order, letter, new_value)}\n"
        f"{total}{row_number}에는 수식이 아니라 숫자가 그대로 적혀 있어서, "
        f"함께 고치지 않으면 예전 합계 그대로 남습니다."
    )
    if len(head + body) <= MAX_REASON:
        return head + body
    # 항목 이름이 길면 나열을 빼고 개수만 밝힌다.
    return f"{opening}값 {len(used)}가지를 더한 합계입니다.{body}"
