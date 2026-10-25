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
from app.agent.query.tabular_request_operations import operation_matches
from app.agent.query.tabular_advanced_language import advanced_operations_match, categorical_request_text
from app.agent.query.tabular_having_language import without_checked_having


def matches_constraints(question, plan, table, tables, *, streaming=False) -> bool:
    text = _without_source_names(question, tables)
    # The current plan's filters are conjunctions. Never interpret an explicit
    # OR request as AND, even if all individual filter values occur in it.
    if re.search(r"\b(?:or|either)\b|또는|혹은", without_literals(text), re.I):
        return False
    if not advanced_operations_match(text, plan, table):
        return False
    predicate_text = without_checked_having(text, plan, table)
    if predicate_text is None:
        return False
    if not grouping_constraints_match(text, plan, table) or not operation_matches(text, plan, table):
        return False
    if not categories_match(categorical_request_text(predicate_text, plan, text, table), plan, table):
        return False
    if not extra_filters_supported(text, plan, table):
        return False
    ranking_ok, rank_filters = ranking_constraints_match(text, plan, table, streaming=streaming)
    return ranking_ok and numeric_constraints_match(predicate_text, plan, table, rank_filters)


def _without_source_names(question, tables):
    text = question
    captions = {str(value) for table in tables for _, value in table.context
                if isinstance(value, str) and len(value.strip()) >= 4}
    # A table titled TOP 30 HOLDERS is a source scope, not a user-requested top-N.
    for caption in sorted(captions, key=len, reverse=True):
        text = re.sub(re.escape(caption), " ", text, flags=re.I)
    return text

