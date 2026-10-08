"""숫자 바로 뒤에 붙은 증감 표현. 그 숫자는 '바꿀 값'이 아니라 '바꿀 양'이다."""
DIRECTION_WINDOW = 12
UP = ("올려", "올리", "인상", "증가", "늘려", "늘리", "상향", "더해", "더하", "추가",
      "높여", "높이", "확대", "증액", "키워", "키우",
      "increase", "raise", "up", "add")
DOWN = ("내려", "내리", "인하", "감소", "줄여", "줄이", "하향", "삭감", "빼", "차감",
        "낮춰", "낮추", "깎", "할인", "축소", "감액", "절감", "덜어",
        "decrease", "reduce", "cut", "down", "less")


def direction_after(instruction: str, end: int) -> int:
    """멀리 떨어진 낱말은 보지 않는다. 1이면 증가, -1이면 감소, 0이면 없음."""
    tail = instruction[end : end + DIRECTION_WINDOW].casefold()
    if any(word in tail for word in DOWN):
        return -1
    return 1 if any(word in tail for word in UP) else 0
