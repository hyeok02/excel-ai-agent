"""A scalar cell cannot answer a requested comparison or aggregation."""
import re
from app.agent.query.search_terms import normalized_query_tokens

HEADER_CONTEXT = {"total", "value", "amount", "수", "값", "전체"}

OPERATIONS = re.compile(
    r"변화|변동|증감|추이|비교|평균|중앙값|합계|총합|최대|최소|최고|최저|"
    r"가장|항목별|부서별|직무별|"
    r"\b(?:change[sd]?|trend|compar\w*|average|mean|median|sum|total|"
    r"maximum|minimum|highest|lowest|count)\b",
    re.I,
)


def scalar_lookup_question(question: str, header: str, label: str = "") -> bool:
    residue = question.casefold()
    for name in (header, label):
        if name:
            residue = residue.replace(name.casefold(), " ")
    return OPERATIONS.search(residue) is None


def lookup_header_matches(question: str, header: str) -> bool:
    """Shared words such as 'Total' cannot substitute Employees for Debt."""
    tokens = set(normalized_query_tokens(header))
    required = tokens - HEADER_CONTEXT
    normalized = question.casefold()
    return bool(tokens) and all(
        word in normalized if not word.isascii()
        else bool(re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", normalized))
        for word in (required or tokens)
    )
