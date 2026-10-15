"""Check explicit request predicates independently of a model-selected plan.

Source labels and category values provide the vocabulary. Grammar only tells us
whether the user requested an equality, exclusion, comparison or ranking; there
are no workbook/company-specific terms or addresses here.
"""
import re

from app.agent.query.tabular_request_numeric import numeric_constraints_match
from app.agent.query.tabular_request_ranking import ranking_constraints_match
from app.agent.query.tabular_request_extras import extra_filters_supported
from app.agent.query.tabular_request_categories import categories_match
from app.agent.query.tabular_request_literals import without_literals


def matches_constraints(question, plan, table, tables) -> bool:
    text = _without_source_names(question, tables)
    # The current plan's filters are conjunctions. Never interpret an explicit
    # OR request as AND, even if all individual filter values occur in it.
    if re.search(r"\b(?:or|either)\b|또는|혹은", without_literals(text), re.I):
        return False
    if not _statistic_matches(text, plan):
        return False
    if not categories_match(text, plan, table):
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
