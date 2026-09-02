import re
from decimal import Decimal

from app.services.insights.numeric_validation import numbers, unmatched_numbers

TOKEN_PATTERN = re.compile(
    r"[A-Za-z]{1,3}\d+|[A-Za-z]+|[가-힣]{2,}|\d[\d,]*(?:\.\d+)?"
)
COLUMN_PATTERN = re.compile(r"^([A-Za-z]{1,3})\d+$")


def grounded_review_point(
    value: str | None, grounded_terms: list[str], cited_numbers: set[Decimal]
) -> str | None:
    """인용한 근거에 실제로 등장하는 것만 가리키는 검토 포인트를 남긴다.

    업종별 추측 표현 목록을 두는 대신 세 단계로 본다. 근거에서 확인되지 않는
    수치를 말하면 버리고, 확인된 수치를 말하면 남기고, 수치가 없으면 근거
    문자열이나 워크북 어휘와 공유하는 대상(셀·열·수식·머리글 단어)이 있을
    때만 남긴다. 파일 밖의 사정을 끌어오는 문장은 어떤 업종의 표현이든
    워크북과 공유할 대상이 없으므로 남지 않는다.
    """
    text = (value or "").strip()
    if not text:
        return None
    if unmatched_numbers(text, cited_numbers):
        return None
    if numbers(text):
        return text
    cited = {token for item in grounded_terms for token in _tokens(item)}
    return text if _tokens(text) & cited else None


def _tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in TOKEN_PATTERN.findall(text):
        tokens.add(raw.casefold())
        if match := COLUMN_PATTERN.match(raw):
            tokens.add(match.group(1).casefold())
    return tokens
