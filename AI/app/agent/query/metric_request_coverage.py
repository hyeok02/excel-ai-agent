"""A scalar shortcut must account for the whole request, not one keyword.

Known source labels/entities plus bounded calendar and operation language may
be consumed. Remaining qualifiers (populations, conversions, other measures,
ratios, filters) must go through a richer planner instead of being discarded.
"""

import re

from app.agent.query.metric_observation_periods import GRAINS, SCENARIOS, LATEST
from app.agent.query.metric_observations import _normal
from app.agent.query.question_date_mentions import calendar_mentions
from app.agent.query.search_terms import KOREAN_SUFFIXES, SEMANTIC_ALIASES
from app.agent.tools.workbook_metric_vocabulary import GENERIC_METRIC_STEMS, GENERIC_METRIC_WORDS

_OPERATIONS = {
    "이", "해당", "파일", "시트", "내", "에서", "의", "에", "과", "와", "로", "및", "혹은",
    "종료", "기준일", "기준일자", "날짜", "날", "같은", "동일", "시작", "마지막", "끝",
    "실제", "실적", "예상", "추정", "단위", "금액", "증가율", "감소율", "증감률", "비율",
    "몇", "명", "총", "전체", "각각", "얼마야", "무엇이야", "뭐야", "기준으로", "값으로",
    "년", "월", "일", "실적과", "예상과", "actual", "actuals", "estimate", "estimates",
    "year", "years", "fiscal", "fy", "quarter", "quarterly", "annual", "month", "monthly",
    "forecast", "budget", "ended", "ending", "date", "dates", "period", "periods", "as",
    "same", "with", "versus", "vs", "between", "growth", "rate", "percentage", "percent",
    "difference", "delta", "unit", "units", "amounts", "both", "each", "respectively", "also",
    "last", "most", "inc", "llc", "ltd", "return", "give", "has", "changed", "me", "since",
}
_STEMS = (*GENERIC_METRIC_STEMS, "비교", "구분", "알려", "보여", "말해", "증가", "감소", "어떻")
_QUESTION_GRAMMAR = re.compile(
    r"(?:얼마|무엇|뭐|몇|몇\s*(?:명|건|개|곳)|명|건|개|곳)"
    r"(?:입니까|인가요|인지|인가|이야|야|이죠|이지요|이지|일까요|일까)?$"
)


def request_covered(question, observations, named_sheets):
    return not uncovered_request_tokens(question, observations, named_sheets)


def uncovered_request_tokens(question, observations, named_sheets):
    consumed = question.casefold()
    for start, end, *_ in reversed(calendar_mentions(consumed)):
        consumed = consumed[:start] + " " * (end - start) + consumed[end:]
    for pattern in [*GRAINS.values(), *SCENARIOS.values(), LATEST]:
        consumed = pattern.sub(" ", consumed)
    labels = {str(item.label.value) for item in observations}
    entities = {str(cell.value) for item in observations for cell in item.entity_cells}
    # An explicit parenthesized source identifier is sufficient to select the
    # row; keep the source identifier (not its user-supplied alias) in output.
    for match in list(re.finditer(r"[가-힣a-z0-9_]+\s*\(([^)]+)\)", consumed)):
        if any(_normal(match[1]) == _normal(entity) for entity in entities):
            consumed = consumed.replace(match[0], match[1])
    for label in sorted([*labels, *entities, *named_sheets], key=len, reverse=True):
        consumed = _remove_source_phrase(consumed, label)
    for entity in entities:
        for token in re.findall(r"[a-z0-9_가-힣]+", entity.casefold()):
            consumed = _remove_source_phrase(consumed, token)
    # Remove aliases only when they name the complete source metric, not when
    # they are a substring of a differently qualified requested measure.
    for label in labels:
        simple = _normal(re.sub(r"\([^)]*\)|\b(?:total|latest)\b", " ", label, flags=re.I))
        for concept, aliases in SEMANTIC_ALIASES.items():
            if simple not in {_normal(value) for value in (concept, *aliases)}:
                continue
            for alias in (concept, *aliases):
                consumed = _remove_source_phrase(consumed, alias)
    allowed = GENERIC_METRIC_WORDS | _OPERATIONS | set(KOREAN_SUFFIXES)
    missing = []
    for token in re.findall(r"[a-z0-9_가-힣]+", consumed):
        if _QUESTION_GRAMMAR.fullmatch(token):
            continue
        forms = {token}
        forms.add(re.sub(r"(?:인가요|인가|이야|야|이지|이지요|일까)$", "", token))
        for suffix in KOREAN_SUFFIXES:
            if token.endswith(suffix) and len(token) > len(suffix):
                forms.add(token[:-len(suffix)])
        if not forms & allowed and not any(form.startswith(_STEMS) for form in forms):
            missing.append(token)
    return missing


def _remove_source_phrase(text, source):
    if not source.strip():
        return text
    # First consume the actual source spelling, including unit punctuation.
    # Dropping only words from "Share (%)" used to leave a stray % that was
    # then misclassified as an unrequested ratio calculation.
    particles = "|".join(map(re.escape, sorted(KOREAN_SUFFIXES, key=len, reverse=True)))
    literal = r"(?<![a-z0-9_가-힣])" + r"\s+".join(map(re.escape, source.casefold().split()))
    text = re.sub(literal + r"(?:" + particles + r")?(?![a-z0-9_가-힣])", " ", text)
    tokens = re.findall(r"[a-z0-9_가-힣]+", source.casefold())
    if not tokens:
        return text
    pattern = r"(?<![a-z0-9_가-힣])"
    if re.search(r"[가-힣]", source):
        pattern += r"(?:총|전체)?"
    pattern += r"[^a-z0-9_가-힣]*".join(map(re.escape, tokens))
    pattern += r"(?:액|수)?(?:" + particles + r")?(?![a-z0-9_가-힣])"
    return re.sub(pattern, " ", text)
