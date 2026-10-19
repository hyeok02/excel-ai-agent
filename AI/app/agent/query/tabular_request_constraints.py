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
from app.agent.query.tabular_request_grouping import grouping_constraints_match
from app.agent.query.ambiguity_labels import label_base


def matches_constraints(question, plan, table, tables, *, streaming=False) -> bool:
    text = _without_source_names(question, tables)
    # The current plan's filters are conjunctions. Never interpret an explicit
    # OR request as AND, even if all individual filter values occur in it.
    if re.search(r"\b(?:or|either)\b|또는|혹은", without_literals(text), re.I):
        return False
    if not grouping_constraints_match(text, plan, table) or not _statistic_matches(text, plan, table):
        return False
    if not categories_match(text, plan, table):
        return False
    if not extra_filters_supported(text, plan, table):
        return False
    ranking_ok, rank_filters = ranking_constraints_match(text, plan, table, streaming=streaming)
    return ranking_ok and numeric_constraints_match(text, plan, table, rank_filters)


def _without_source_names(question, tables):
    text = question
    captions = {str(value) for table in tables for _, value in table.context
                if isinstance(value, str) and len(value.strip()) >= 4}
    # A table titled TOP 30 HOLDERS is a source scope, not a user-requested top-N.
    for caption in sorted(captions, key=len, reverse=True):
        text = re.sub(re.escape(caption), " ", text, flags=re.I)
    return text


def _statistic_matches(text, plan, table):
    patterns = {
        "sum": r"합계|총합|\bsum\b|\btotal\b",
        "average": r"평균|\baverage\b|\bmean\b",
        "min": r"최솟값|최소값|\bminimum\b",
        "max": r"최댓값|최대값|\bmaximum\b",
    }
    text = without_literals(text)
    labels = {label for column in table.columns for label in (column.header, label_base(column.header))}
    for label in sorted(labels, key=len, reverse=True):
        # An isolated operator/column-name collision is ambiguous, not proof
        # that the user did not ask for an aggregate.
        if not any(re.fullmatch(pattern, label, re.I) for pattern in patterns.values()):
            text = re.sub(r"(?<![\w])" + re.escape(label) + r"(?![A-Za-z0-9_])", " ", text, flags=re.I)
    requested = {key for key, pattern in patterns.items() if re.search(pattern, text, re.I)}
    if plan.operation != "numeric_summary":
        return not requested if plan.order_by else True
    if getattr(plan, "group_by", ()):
        return (not requested and plan.statistic == "all") or requested == {plan.statistic}
    return not requested or plan.statistic == "all" or requested == {plan.statistic}
