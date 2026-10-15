"""Safe matching between a question and one time-series metric."""

from app.agent.query.search_terms import SEMANTIC_ALIASES
from app.services.insights.display.glossary import readable
from app.agent.tools.workbook_metric_vocabulary import GENERIC_METRIC_STEMS, GENERIC_METRIC_WORDS, METRIC_ALIAS_COMPOUNDS
from app.agent.tools.workbook_metric_tokens import (
    DATE_TERM, forms, phrase_in, requirement_matches, sequence, words,
)
CONTEXT_CONCEPTS = {"직원", "인원", "부서"}
IDENTITY_GROUPS = (("전체 직원", "전체 인원", "직원수", "인원수", "headcount", "total employees"),)
ALIAS_GROUPS = (*IDENTITY_GROUPS, *(
    (concept, *METRIC_ALIAS_COMPOUNDS.get(concept, ()), *aliases)
    for concept, aliases in SEMANTIC_ALIASES.items()
))
ALIAS_REQUIREMENTS = {frozenset(group) for group in ALIAS_GROUPS}


def complete_metric(metric: dict) -> bool:
    required = ("header", "start_value", "end_value", "change", "start_reference", "end_reference")
    return (
        all(metric.get(key) is not None for key in required)
        and isinstance(metric["header"], str)
        and bool(metric.get("header_references"))
    )


def unique_named_metric(
    metrics: list[object], question: str, targets: tuple[str, ...] = ()
) -> dict | None:
    ranked = [
        (score, metric)
        for metric in metrics
        if isinstance(metric, dict) and complete_metric(metric)
        if (score := metric_score(metric, question, targets))
    ]
    ranked.sort(key=lambda item: -item[0])
    if not ranked or len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        return None
    return ranked[0][1]


def metric_score(metric: dict, question: str, targets: tuple[str, ...]) -> int:
    """Every non-generic condition in the question must describe the metric."""
    raw_header = str(metric["header"])
    header = raw_header.casefold()
    translated_header = readable(raw_header).casefold()
    searchable_header = f"{header} {translated_header}"
    requirements = _requirements(question)
    if requirements and not all(
        any(requirement_matches(value, item, question, ALIAS_REQUIREMENTS)
            for value in (header, translated_header))
        for item in requirements
    ):
        return 0
    target_score = max(
        (_target_score(searchable_header, target) for target in targets), default=0
    )
    if not requirements and not target_score:
        return 0
    exact = max(
        (_phrase_score(raw_header, source) for source in (question, *targets)), default=0
    )
    return sum(max(map(len, item)) for item in requirements) + target_score + exact


def contains_term(text: str, term: str) -> bool:
    return phrase_in(text, term)


def has_extra_metric_identity(text: str) -> bool:
    return any(item != frozenset(IDENTITY_GROUPS[0]) for item in _requirements(text))

def _requirements(text: str) -> list[frozenset[str]]:
    source = words(text)
    covered: set[int] = set()
    found: list[frozenset[str]] = []
    for index, word in enumerate(source[1:], 1):
        if len(word) == 1 and word.isascii() and not _generic(forms(source[index - 1])):
            covered.update((index - 1, index))
            found.append(frozenset((f"{source[index - 1]} {word}",)))
    for group in ALIAS_GROUPS:
        match = next(
            (
                value
                for alias in group
                if (value := sequence(source, alias)) is not None
            ),
            None,
        )
        if match is None or match & covered:
            continue
        covered.update(match)
        if group[0] not in CONTEXT_CONCEPTS and not _generic({group[0]}):
            found.append(frozenset(group))
    for index, word in enumerate(source):
        variants = forms(word)
        if index in covered or _generic(variants) or any(DATE_TERM.fullmatch(item) for item in variants):
            continue
        if max(map(len, variants)) >= 2:
            found.append(frozenset(variants))
    unique = list(dict.fromkeys(found))
    return [item for item in unique if len(unique) == 1 or item != frozenset(IDENTITY_GROUPS[0])]


def _generic(forms: set[str]) -> bool:
    return bool(forms & GENERIC_METRIC_WORDS) or any(
        form.startswith(GENERIC_METRIC_STEMS) for form in forms
    )


def _target_score(header: str, target: str) -> int:
    return 20 if phrase_in(header, target) else 0


def _phrase_score(header: str, source: str) -> int:
    return sum(map(len, words(header))) if phrase_in(source, header) else 0
