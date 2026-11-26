"""Requests that change a sheet's shape or look, not its cell values: answered before the model is asked.

"영업 부서 직원 행을 삭제해줘" cannot be done by changing values; blanking the eight rows' cells would leave
empty rows the user did not ask for. Adding or removing rows, columns or sheets, sorting and formatting are
named back to the user as not supported. Quoted replacement text ('삭제 완료') is not read as the request.
"""
import re

SHAPE = re.compile(
    r"(?:행|열|줄|\brows?|\bcolumns?)\s*(?:을|를|들을|들)?\s*(?:전부\s*|모두\s*|하나\s*)?"
    r"(?:삭제|지워|지우|없애|제거|추가|삽입|끼워|delete|remove|insert|add)"
    r"|\b(?:delete|remove|insert|add)\s+(?:the\s+|a\s+|new\s+)?(?:\w+\s+)?(?:rows?|columns?|sheets?)\b"
    r"|정렬|\bsort\b|새\s*시트|시트를?\s*(?:새로\s*)?(?:추가|만들|생성)"
    r"|서식|굵게|글꼴|폰트|테두리|열\s*너비|보기\s*좋게|색(?:깔|상)?을?\s*(?:바꿔|칠|넣|입혀)|\bbold\b|\bhighlight",
    re.I)
MESSAGE = ("행·열이나 시트를 추가·삭제하거나 정렬·서식을 바꾸는 요청은 아직 지원하지 않습니다. "
           "셀 값을 바꾸거나 비우는 요청만 처리할 수 있습니다.")


def unsupported_request(instruction: str) -> str | None:
    unquoted = re.sub(r"(['\"‘“]).*?(['\"’”])", " ", instruction)
    return MESSAGE if SHAPE.search(unquoted) else None
