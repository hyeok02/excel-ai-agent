"""Conservative semantic matching for source-verified workbook insights."""

import re

from app.agent.query.search_terms import (
    KOREAN_SUFFIXES,
    SEMANTIC_ALIASES,
    normalized_query_tokens,
    search_terms,
)
from app.agent.query.verified_insight_constraints import (
    contains_term,
    required_concepts_match,
    semantic_tags,
)

MIN_RELEVANCE_SCORE = 8
_TOKENS = re.compile(r"[0-9a-zA-Z_]+|[가-힣]+")
_GENERIC = {
    "값", "결과", "자료", "수치", "전체", "항목", "항목별", "현황",
    "변화", "변동", "추이", "비교", "표시별", "건수", "개수", "기간별",
    "직원", "인원", "수", "얼마나", "가장", "제일", "최근", "data",
    "result", "total", "value", "trend", "change", "how", "much",
    "latest", "recent",
}
_GENERIC_STEMS = ("늘어", "늘었", "줄어", "줄었", "변했", "달라졌")
_REQUESTS = {"알려줘", "보여줘", "말해줘", "설명해줘", "뭐야", "무엇", "어떤", "어떻게",
             "비교해줘", "요약해줘", "정리해줘", "please", "show", "tell", "what"}
# How to show a fact, not which fact (incl. the app's own follow-up questions,
# e.g. "… 관련 수치와 원본 근거를 보여줘"); never required inside the insight.
_REQUEST_WORDING = {"관련", "수치", "원본", "근거", "항목별", "시작", "처음", "최초", "값", "마지막", "기준",
                    "함께", "기록된", "확인된", "내용", "표시별", "요약", "설명"}
_ALIAS_GROUPS = tuple((concept, *values) for concept, values in SEMANTIC_ALIASES.items())
_ALIAS_TERMS = {value for values in _ALIAS_GROUPS for value in values}


def verified_insight_score(
    question: str, asked: str, item: dict[str, object]
) -> int:
    text = _searchable_text(item)
    if not required_concepts_match(asked, text):
        return 0
    identities = _identity_requirements(question)
    if identities and not all(
        any(contains_term(text, term) for term in group) for group in identities
    ):
        return 0
    title = str(item.get("title") or "").casefold()
    terms = [term for term in _canonical_terms(asked) if not _request_word(term)]
    direct = {
        term for term in _canonical_terms(question)
        if term not in _ALIAS_TERMS and not _request_word(term)
    }
    requested_identity = {term for term in direct if term not in _GENERIC}
    distinctive = {
        term for term in direct if term not in _GENERIC and contains_term(text, term)
    }
    direct_title = {term for term in direct if contains_term(title, term)}
    direct_fact = {term for term in direct if contains_term(text, term)}
    alias_groups = sum(
        any(term in terms and contains_term(text, term) for term in aliases)
        for aliases in _ALIAS_GROUPS
    )
    target_match = _target_matches(question, asked, text)
    if requested_identity and not distinctive and not target_match:
        return 0
    if not distinctive and not target_match and not alias_groups and not direct_title:
        return 0
    score = sum(min(len(term), 8) for term in direct_fact)
    score += 3 * sum(min(len(term), 8) for term in direct_title)
    score += 4 * alias_groups + 8 * len(distinctive)
    score += 20 * int(target_match) + _phrase_bonus(question, title)
    return score


def _searchable_text(item: dict[str, object]) -> str:
    base = " ".join(
        str(item.get(key) or "") for key in ("title", "topic", "category", "fact")
    ).casefold()
    return f"{base} {semantic_tags(base)}"


def _canonical_terms(text: str) -> list[str]:
    """Drop an inflected spelling when its particle-free form is also present."""
    terms = search_terms(text)
    values = set(terms)
    return [
        term
        for term in terms
        if not any(
            len(term) > len(suffix) and term[: -len(suffix)] in values
            for suffix in KOREAN_SUFFIXES
            if term.endswith(suffix)
        )
    ]


def _identity_requirements(text: str) -> list[frozenset[str]]:
    raw = normalized_query_tokens(text)
    values = set(raw)
    terms = [
        term for term in raw
        if len(term) >= 2 and not _identity_generic(term) and term not in _REQUESTS
        and not any(
            len(term) - len(suffix) >= 2 and term[: -len(suffix)] in values
            for suffix in KOREAN_SUFFIXES if term.endswith(suffix)
        )
    ]
    groups = []
    for term in terms:
        matched = next((group for group in _ALIAS_GROUPS if term in group), None)
        groups.append(frozenset(matched or (term,)))
    return list(dict.fromkeys(groups))


def _identity_generic(term: str) -> bool:
    return term in _GENERIC or _request_word(term) or term.startswith(_GENERIC_STEMS)


def _request_word(term: str) -> bool:
    base = re.sub(r"(?:으로|로|와|과|을|를|의|에|은|는)$", "", term)
    return term in _REQUESTS or base in _REQUESTS or base in _REQUEST_WORDING


def _target_matches(question: str, asked: str, text: str) -> bool:
    if asked == question:
        return False
    targets = asked.removeprefix(question).strip().casefold()
    return len(targets) >= 2 and contains_term(text, targets)


def _phrase_bonus(question: str, title: str) -> int:
    question_tokens = [
        token for token in _TOKENS.findall(question.casefold())
        if not _request_word(token)
    ]
    title_tokens = _TOKENS.findall(title)
    longest = 0
    for start in range(len(question_tokens)):
        for end in range(start + 1, len(question_tokens) + 1):
            phrase = question_tokens[start:end]
            if any(
                title_tokens[index : index + len(phrase)] == phrase
                for index in range(len(title_tokens) - len(phrase) + 1)
            ):
                longest = max(longest, end - start)
    return longest * 5
