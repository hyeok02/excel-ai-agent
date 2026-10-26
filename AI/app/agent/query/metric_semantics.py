"""Keep metric aliases inside the meaning established by source headers."""
import re

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.metric_observation_cells import metric_label_matches, _normal
from app.agent.query.search_terms import SEMANTIC_ALIASES

_CATEGORIES = re.compile(r"\b(?:roles?|departments?|functions?|divisions?)\b|직무|부서", re.I)
_FINANCIAL = ("매출", "영업이익", "순이익", "자산", "부채", "현금")
_PEOPLE_UNITS = frozenset(("명", "인", "인원", "people", "person", "persons", "employee", "employees", "headcount"))


def column_metric_matches(column, question):
    return metric_label_matches(column.header, question) and not column_metric_conflict(column, question)


def column_metric_conflict(column, question):
    """A category named like a measure is not that measure (e.g. Sales roles)."""
    if not any(_CATEGORIES.search(text) for _, text in column.context) and not people_number_formats(column):
        return False
    label = _normal(column.header)
    # Naming the category does not erase another explicitly requested measure:
    # "Sales 부서의 Revenue" still requires revenue, not the Sales headcount.
    for concept in _FINANCIAL:
        names = (concept, *SEMANTIC_ALIASES[concept])
        if label not in {_normal(name) for name in names}:
            continue
        # Sales alone is ambiguous vocabulary, not an explicit revenue request.
        unambiguous = [name for name in names if _normal(name) != label]
        if any(metric_label_matches(name, question) and _mentioned(name, question) for name in unambiguous):
            return True
    return False


def people_number_formats(column):
    """Only explicit person units count; currency per person is not headcount."""
    formats = []
    for number_format in column.number_formats:
        spec = parse_number_format(number_format)
        if any(affix.strip().casefold() in _PEOPLE_UNITS for affix in (spec.prefix, spec.suffix)):
            formats.append(number_format)
    return tuple(dict.fromkeys(formats))


def _mentioned(label, question):
    from app.agent.query.metric_observation_cells import _korean_metric_in_question
    if re.search(r"[가-힣]", label):
        return _korean_metric_in_question(label, question)
    return bool(re.search(r"(?<!\w)" + re.escape(_normal(label)) + r"(?!\w)", _normal(question)))
