import re
from decimal import Decimal

from app.services.insights.numeric_validation import numbers, unmatched_numbers

TOKEN_PATTERN = re.compile(
    r"\d+[가-힣]+|[A-Za-z]{1,3}\d+|[A-Za-z]+|[가-힣]{2,}|\d[\d,]*(?:\.\d+)?"
)
COLUMN_PATTERN = re.compile(r"^([A-Za-z]{1,3})\d+$")
NAME_PATTERN = re.compile(r"^(\d+)([가-힣]+)$")
NAME_IN_TEXT_PATTERN = re.compile(r"\d+[가-힣]+")


def grounded_tokens(grounded_terms: list[str]) -> set[str]:
    """근거와 워크북 어휘에서 대조에 쓸 토큰을 모은다."""
    return {token for item in grounded_terms for token in _tokens(item)}


def mask_known_names(text: str, grounded: set[str]) -> str:
    """'2공장', '1호기'처럼 워크북에 있는 이름 속 숫자를 수치 주장에서 뺀다.

    제조·설비 데이터에서 이름에 숫자가 붙는 것은 흔한 일이라, 그 숫자를
    근거 없는 수치로 오해하면 정상적인 문장이 통째로 버려진다.
    """
    names = {token for token in grounded if NAME_PATTERN.match(token)}
    if not names:
        return text
    return NAME_IN_TEXT_PATTERN.sub(
        lambda match: " "
        if any(match.group(0).casefold().startswith(name) for name in names)
        else match.group(0),
        text,
    )


def grounded_review_point(
    value: str | None, grounded: set[str], cited_numbers: set[Decimal]
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
    masked = mask_known_names(text, grounded)
    if unmatched_numbers(masked, cited_numbers):
        return None
    if numbers(masked):
        return text
    return text if _tokens(text) & grounded else None


def _tokens(text: str) -> set[str]:
    tokens: set[str] = set()
    for raw in TOKEN_PATTERN.findall(text):
        tokens.add(raw.casefold())
        if match := COLUMN_PATTERN.match(raw):
            tokens.add(match.group(1).casefold())
        if match := NAME_PATTERN.match(raw):
            tokens.add(match.group(2).casefold())
    return tokens
