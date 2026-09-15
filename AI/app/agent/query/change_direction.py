"""답변이 말한 증감 방향이 원본 값의 변화 방향과 같은지 확인한다.

차이와 증감률은 절댓값으로 대조하므로, 방향을 따로 보지 않으면
"6,101명에서 5,417명으로 684명 증가"처럼 뒤집힌 문장도 통과한다.
"A에서 B로 …했다" 형태, 즉 한 절에 인용 셀 값이 정확히 두 개 있을 때만
판단한다. 값이 더 많으면 무엇과 무엇을 비교했는지 알 수 없어 넘긴다.
"""
import re

from app.agent.query.derived_numbers import stated_cell_values

# 천 단위 구분 기호와 소수점을 문장 구분으로 착각하지 않도록
# 숫자가 뒤따르는 쉼표와 마침표는 절 경계로 보지 않는다.
CLAUSE = re.compile(r"[!?;\n]|[.,](?!\d)|(?:이고|이며|반면|그리고)")
INCREASE = re.compile(r"증가|증대|늘어|늘었|상승|increas|grew|rose|growth", re.I)
DECREASE = re.compile(r"감소|축소|줄어|줄었|하락|decreas|fell|declin|drop", re.I)


def answer_directions_supported(answer: str, evidence: list[object]) -> bool:
    for clause in CLAUSE.split(answer):
        direction = stated_direction(clause)
        if direction is None:
            continue
        values = stated_cell_values(clause, evidence)
        if len(values) != 2:
            continue
        change = values[1] - values[0]
        if change == 0 or (change > 0) is not (direction == "increase"):
            return False
    return True


def stated_direction(text: str) -> str | None:
    increase = bool(INCREASE.search(text))
    decrease = bool(DECREASE.search(text))
    if increase == decrease:
        return None
    return "increase" if increase else "decrease"
