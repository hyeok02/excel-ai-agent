"""Safety constraints shared by verified-insight answer paths."""

import re

_REQUIRED_CONCEPTS = (
    ("평균", "average", "mean", "avg"),
    ("중앙값", "median"),
    ("합계", "총합", "sum"),
    (
        "최고", "최대", "가장 높은", "가장 많", "1위", "highest",
        "maximum", "max", "top",
    ),
    ("최저", "최소", "가장 낮은", "lowest", "minimum", "min"),
    ("몇 개", "몇개", "개수", "건수", "how many", "count"),
    ("최근", "가장 최근", "latest", "recent"),
)
_CHANGE_MARKERS = (
    "변화", "변동", "증감", "추이", "비교", "달라", "변했", "감소", "증가",
    "줄어", "줄었", "늘어", "늘었", "change", "trend", "compar", "decreas",
    "increas", "grew", "fell", "rose",
)
_OVER_TIME = re.compile(r"변화|변동|증감|추이|변했|달라졌|늘었|줄었|늘어|줄어|"
                        r"(?:시작|처음|최초).*(?:마지막|최근|끝)|\b(?:change|trend|grew|fell|rose)\b", re.I)
_COUNT_VALUE = re.compile(r"(?<!\d)\d[\d,]*(?:건|개|명|대)(?![가-힣])")


def required_concepts_match(question: str, text: str) -> bool:
    normalized = question.casefold()
    if not requested_identifiers_match(normalized, text):
        return False
    years = set(re.findall(r"(?:19|20)\d{2}", normalized))
    if years and not years.issubset(set(re.findall(r"(?:19|20)\d{2}", text))):
        return False
    if not _specific_dates_match(normalized, text):
        return False
    ranks = _ranks(normalized)
    if ranks and not ranks.issubset(_ranks(text)):
        return False
    for aliases in _REQUIRED_CONCEPTS:
        required = any(contains_term(normalized, alias) for alias in aliases)
        present = any(contains_term(text, alias) for alias in aliases)
        if aliases[0] == "몇 개" and _COUNT_VALUE.search(text):
            present = True
        if required and not present:
            return False
    return True


def requested_identifiers_match(question: str, text: str) -> bool:
    """A fact about CVD #1 cannot answer a request for nonexistent CVD #99."""
    identifiers = re.findall(r"#\s*([0-9a-z][0-9a-z_-]*)", question)
    return all(contains_term(text, identifier) for identifier in identifiers)


def insight_intent_matches(
    question: str, item: dict[str, object], answer_kind: str = ""
) -> bool:
    category = str(item.get("category") or "").casefold()
    if not category:
        return True
    if category not in {"change", "trend"}:
        # A snapshot cannot answer a change over time; words inside the
        # insight's own title ("비교군 중앙값") are its name, not the request.
        asked = question.casefold()
        for label in (item.get("title"), item.get("topic")):
            asked = asked.replace(str(label or "").casefold() or "\0", " ")
        return not _OVER_TIME.search(asked)
    normalized = question.casefold()
    return any(
        marker in normalized for marker in _CHANGE_MARKERS
    )


def semantic_tags(text: str) -> str:
    tags = []
    if "1위" in text and ("비중" in text or "%" in text):
        tags.append(
            "최대 가장 많은 주주 보유자 지분율 비중 owner holder shareholder "
            "ownership percent held top rank maximum highest"
        )
    event_record = "기록되어 있습니다" in text or any(
        marker in text for marker in ("announced date", "event type", "headline:")
    )
    if event_record and re.search(r"(?:19|20)\d{2}년", text):
        tags.append(
            "최근 이벤트 소식 발표 latest recent event development announcement"
        )
    return " ".join(tags)


def contains_term(text: str, phrase: str) -> bool:
    if not phrase.isascii():
        return phrase in text
    return bool(
        re.search(rf"(?<![a-z0-9_]){re.escape(phrase)}(?![a-z0-9_])", text)
    )


def _specific_dates_match(question: str, text: str) -> bool:
    pattern = r"((?:19|20)\d{2})\s*년\s*(\d{1,2})\s*월(?:\s*(\d{1,2})\s*일)?"
    asked = {(int(y), int(m), int(d) if d else None) for y, m, d in re.findall(pattern, question)}
    found = [(int(y), int(m), int(d) if d else None) for y, m, d in re.findall(pattern, text)]
    return all(
        any(y == fy and m == fm and (d is None or d == fd) for fy, fm, fd in found)
        for y, m, d in asked
    )


def _ranks(text: str) -> set[int]:
    values = re.findall(r"(?<!\d)(\d+)\s*위", text)
    values += re.findall(r"\b(?:rank|top)\s*(\d+)\b", text)
    values += re.findall(r"상위\s*(\d+)", text)
    return {int(value) for value in values}
