"""관련 셀을 왜 함께 고쳐야 하는지 화면에 보여 줄 조각으로 만든다.

열 문자(AI, G, W …)는 읽는 사람에게 아무 뜻이 없어 열 머리글로 바꾸고,
한 문장으로 뭉치지 않도록 설명·계산식·항목 이름을 따로 돌려준다.
"""
from app.agent.writeback.mirrored_series import column_label
from app.agent.writeback.row_totals import integer


def label(columns, letter: str, row_number: int) -> str:
    """열 머리글. 없으면 셀 주소를 그대로 쓴다."""
    return column_label(columns.get(letter, {}), row_number) or f"{letter}{row_number}"


def _column_order(letter: str) -> tuple[int, str]:
    """엑셀 열 순서. 사전순으로 세우면 AI가 G보다 앞에 온다."""
    return len(letter), letter


def _sum_line(target, order, letter, value) -> str:
    parts = [integer(value if name == letter else target[name]) for name in order]
    return f"{' + '.join(str(part) for part in parts)} = {sum(parts)}"


def total_wording(columns, target, total, letter, row_number, used, new_value) -> dict:
    """합계 셀 설명. reason은 한 문장, 계산식과 항목 이름은 따로 보낸다."""
    order = [*sorted((name for name in used if name != letter), key=_column_order), letter]
    before = integer(target[total])
    return {
        "reason": (
            f"{total}{row_number}은 이 행의 값 {len(used)}개를 더한 "
            f"합계({label(columns, total, row_number)})입니다. 수식이 아니라 숫자가 "
            f"그대로 적혀 있어, 함께 고치지 않으면 {before} 그대로 남습니다."
        ),
        "breakdown": [
            _sum_line(target, order, letter, target[letter]),
            _sum_line(target, order, letter, new_value),
        ],
        "parts": [label(columns, name, row_number) for name in order],
    }
