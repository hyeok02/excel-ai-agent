"""Check explicit request predicates independently of a model-selected plan.

Source labels and category values provide the vocabulary. Grammar only tells us
whether the user requested an equality, exclusion, comparison or ranking; there
are no workbook/company-specific terms or addresses here.
"""
import re

from app.agent.query.tabular_request_numeric import numeric_constraints_match
from app.agent.query.tabular_request_ranking import ranking_constraints_match
from app.agent.query.tabular_request_extras import extra_filters_supported


def matches_constraints(question, plan, table, tables) -> bool:
    text = _without_source_names(question, tables)
    # The current plan's filters are conjunctions. Never interpret an explicit
    # OR request as AND, even if all individual filter values occur in it.
    if re.search(r"\b(?:or|either)\b|또는|혹은", text, re.I):
        return False
    if not _statistic_matches(text, plan):
        return False
    if not _categories_match(text, plan, table):
        return False
    if not extra_filters_supported(text, plan, table):
        return False
    ranking_ok, rank_filters = ranking_constraints_match(text, plan, table)
    return ranking_ok and numeric_constraints_match(text, plan, table, rank_filters)


def _without_source_names(question, tables):
    text = question
    captions = {str(value) for table in tables for _, value in table.context
                if isinstance(value, str) and len(value.strip()) >= 4}
    # A table titled TOP 30 HOLDERS is a source scope, not a user-requested top-N.
    for caption in sorted(captions, key=len, reverse=True):
        text = re.sub(re.escape(caption), " ", text, flags=re.I)
    return text


def _statistic_matches(text, plan):
    if plan.operation != "numeric_summary":
        return True
    patterns = {
        "sum": r"합계|총합|\bsum\b|\btotal\b",
        "average": r"평균|\baverage\b|\bmean\b",
        "min": r"최솟값|최소값|\bminimum\b",
        "max": r"최댓값|최대값|\bmaximum\b",
    }
    requested = {key for key, pattern in patterns.items() if re.search(pattern, text, re.I)}
    return not requested or plan.statistic == "all" or requested == {plan.statistic}


def _categories_match(text, plan, table):
    headers = {_normal(column.header) for column in table.columns}
    matches = []
    for column in table.columns:
        values = {value for row in table.rows
                  if isinstance(value := row.values[column.id], str) and value.strip()}
        for value in values:
            if _normal(value) in headers:
                continue
            match = _value_match(text, value)
            if match:
                matches.append((column.id, value, match))
    # Prefer the longest source value at a position (e.g. a full company name
    # over a short category embedded inside that company name).
    matches = [(column, value, match) for column, value, match in matches
               if not any(other.start() <= match.start() and other.end() >= match.end()
                          and len(other_value) > len(value)
                          for _, other_value, other in matches)]
    for column, value, match in matches:
        candidates = [condition for condition in plan.filters
                      if condition.column_id == column
                      and isinstance(condition.value, str)
                      and _normal(condition.value) == _normal(value)]
        after = text[match.end():match.end() + 16]
        before = text[max(0, match.start() - 16):match.start()]
        negative = bool(re.match(r"\s*(?:이\s*)?(?:아닌|아니|제외|외의)", after)
                        or re.search(r"(?:not|except|excluding)\s*$", before, re.I))
        contains = bool(re.search(r"포함|contains?", before[-10:] + after[:10], re.I))
        operator = "not_equals" if negative else "contains" if contains else "equals"
        if not any(condition.operator == operator for condition in candidates):
            return False
    return True


def _value_match(text, value):
    normalized = str(value).strip()
    if len(normalized) > 300 or re.fullmatch(r"[-+]?\d[\d,./:% -]*", normalized):
        return None
    # Match English identifiers exactly, including when followed by a Korean
    # particle. "A" must not match the beginning of "Amount".
    pattern = rf"(?<![A-Za-z0-9_]){re.escape(normalized)}(?![A-Za-z0-9_])"
    if re.fullmatch(r"[가-힣]+", normalized):
        pattern = rf"(?<![가-힣]){re.escape(normalized)}(?=$|\s|[,.?!'\"]|인|이|가|은|는|을|를|의|와|과|만|에|아닌|제외)"
    return re.search(pattern, text, re.I)


def _normal(value):
    return " ".join(str(value).casefold().split())
