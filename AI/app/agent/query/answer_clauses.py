"""답변을 절 단위로 나누고, 절이 말한 증감 방향을 읽는다.

수치 검증을 답변 전체가 아니라 절 단위로 하기 위한 공통 도구다. 전체
단위로 보면 한 절에서 만들어진 근거가 다른 절의 주장을 통과시킨다.

천 단위 구분 기호와 소수점은 절 경계가 아니다. 숫자가 뒤따르는 쉼표와
마침표를 경계로 보면 "6,101"과 "11.21"이 잘려 검사가 빗나간다.
"""
import re

CLAUSE = re.compile(
    r"[!?;\n]|[.,](?!\d)|(?:이고|이며|반면|그리고)|\b(?:and|while)\b", re.I
)
INCREASE = re.compile(r"증가|증대|늘어|늘었|상승|increas|grew|rose|growth", re.I)
DECREASE = re.compile(r"감소|축소|줄어|줄었|하락|decreas|fell|declin|drop", re.I)


def clauses(text: str) -> list[str]:
    return [part for part in CLAUSE.split(text) if part and part.strip()]


def stated_direction(text: str) -> str | None:
    """절이 증감 중 한쪽만 말하고 있으면 그 방향을 돌려준다."""
    increase = bool(INCREASE.search(text))
    decrease = bool(DECREASE.search(text))
    if increase == decrease:
        return None
    return "increase" if increase else "decrease"
