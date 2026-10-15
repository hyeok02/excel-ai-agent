"""Token and phrase rules shared by safe workbook metric matching."""

import re

from app.agent.query.search_terms import KOREAN_SUFFIXES
from app.agent.tools.workbook_metric_vocabulary import ALIAS_HEADER_MODIFIERS

TOKEN = re.compile(
    r"(?:19|20)\d{2}[./-]\d{1,2}(?:[./-]\d{1,2})?|[0-9가-힣]+|[0-9a-z]+"
)
DATE_TERM = re.compile(
    r"(?:(?:19|20)\d{2}(?:년?(?:\d{1,2}월(?:\d{1,2}일)?)?|"
    r"[./-]\d{1,2}(?:[./-]\d{1,2})?)|\d{1,2}(?:월|일))$"
)


def phrase_in(text: str, phrase: str) -> bool:
    source, wanted = words(text), words(phrase)
    return bool(wanted) and any(
        all(want in forms(source[start + offset]) for offset, want in enumerate(wanted))
        for start in range(len(source) - len(wanted) + 1)
    )


def requirement_matches(
    header: str,
    requirement: frozenset[str],
    question: str,
    alias_requirements: set[frozenset[str]],
) -> bool:
    if not any(phrase_in(header, alternative) for alternative in requirement):
        return False
    if requirement not in alias_requirements:
        return True
    allowed = set(words(question)) | ALIAS_HEADER_MODIFIERS
    allowed.update(
        word for alternative in requirement for word in words(alternative)
    )
    return all(word in allowed for word in words(header))


def sequence(source: list[str], phrase: str) -> set[int] | None:
    wanted = words(phrase)
    if not wanted:
        return None
    for start in range(len(source) - len(wanted) + 1):
        if all(want in forms(source[start + offset]) for offset, want in enumerate(wanted)):
            return set(range(start, start + len(wanted)))
    return None


def words(text: object) -> list[str]:
    return TOKEN.findall(_normalize(text))


def forms(word: str) -> set[str]:
    values = {word}
    for suffix in KOREAN_SUFFIXES:
        if word.endswith(suffix) and len(word) > len(suffix):
            values.add(word[: -len(suffix)])
            break
    return values


def _normalize(text: object) -> str:
    value = str(text or "").casefold()
    return re.sub(
        r"(?<![a-z0-9])r\s*&\s*d(?![a-z0-9])",
        " research development ",
        value,
    )
