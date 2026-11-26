"""숫자 바로 뒤에 붙은 증감 표현. 그 숫자는 '바꿀 값'이 아니라 '바꿀 양'이다.

영어는 동사가 앞에 온다("Increase HoursWorked by 8"). by 바로 뒤 숫자는 앞 동사의 양으로 읽는다.
"1,000으로 올려줘"처럼 '으로'가 붙은 숫자는 올릴 양이 아니라 올린 뒤의 값이다.
"""
import re
DIRECTION_WINDOW = 12
UP = ("올려", "올리", "인상", "증가", "늘려", "늘리", "상향", "더해", "더하", "추가",
      "높여", "높이", "확대", "증액", "키워", "키우",
      "increase", "raise", "up", "add")
DOWN = ("내려", "내리", "인하", "감소", "줄여", "줄이", "하향", "삭감", "빼", "차감",
        "낮춰", "낮추", "깎", "할인", "축소", "감액", "절감", "덜어", "감면",
        "decrease", "reduce", "cut", "down", "less")


def direction_after(instruction: str, end: int) -> int:
    """멀리 떨어진 낱말은 보지 않는다. 1이면 증가, -1이면 감소, 0이면 없음."""
    tail = instruction[end : end + DIRECTION_WINDOW].casefold()
    if any(word in tail for word in DOWN):
        return -1
    return 1 if any(word in tail for word in UP) else 0


TARGET = re.compile(r"\s*(?:명|개|원|건|점|시간|%|퍼센트)?\s*(?:으로|로)(?=\s|$|[.,!?])")
BY = re.compile(r"\bby\s*$", re.I)
ENGLISH_UP, ENGLISH_DOWN = ("increase", "raise", "add"), ("decrease", "reduce", "cut", "lower")


def is_target(instruction: str, end: int) -> bool:
    """'1,000으로 올려줘'의 1,000: 증감 표현이 뒤따라도 바꿀 뒤의 값이다."""
    return TARGET.match(instruction, end) is not None


def direction_before(instruction: str, start: int) -> int:
    """'Increase HoursWorked by 8'의 8: by 앞 영어 동사의 방향."""
    head = instruction[:start]
    if not BY.search(head):
        return 0
    words = head.casefold()
    if any(word in words for word in ENGLISH_DOWN):
        return -1
    return 1 if any(word in words for word in ENGLISH_UP) else 0


def amount_direction(instruction: str, start: int, end: int) -> int:
    """숫자가 '바꿀 양'이면 그 방향, 바꿀 값이면 0."""
    if is_target(instruction, end):
        return 0
    return direction_after(instruction, end) or direction_before(instruction, start)
