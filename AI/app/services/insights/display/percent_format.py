"""엑셀 서식의 %가 '100을 곱해 보여 준다'는 뜻인지 가려낸다."""


def scales_by_percent(number_format: object) -> bool:
    """
    따옴표 안이나 역슬래시 뒤의 %는 곱하라는 기호가 아니라 그냥 글자다.

    0.00"%" 서식은 18.5를 화면에 18.50%로 보여 준다. 이를 백분율 서식으로 보고
    100을 곱하면 보고서에 1,850%라고 적히고, 셀에는 18.5가 있으니 숫자 검증도
    그대로 통과한다.
    """
    text = str(number_format or "")
    quoted = False
    position = 0
    while position < len(text):
        character = text[position]
        if character == "\\":
            position += 2
            continue
        if character == '"':
            quoted = not quoted
        elif character == "%" and not quoted:
            return True
        position += 1
    return False
