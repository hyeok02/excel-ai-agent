"""Source-bound categorical counts, including safe classifier-unavailable paths."""
import re

from app.agent.query.ambiguity_labels import mentioned_sources
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_request_literals import source_headers
from app.agent.query.tabular_request_predicates import categorical_predicates
from app.agent.query.source_count_scope import count_scope_covered

_COUNT = re.compile(r"몇\s*(?:건|개|행|대|곳)|건수|개수|행\s*수|\bhow\s+many\b|\b(?:count|number)\s+of\b", re.I)


def source_count_answer(question, summary, index):
    if not _COUNT.search(question):
        return None
    tables = build_query_tables(summary)
    named = mentioned_sources((table.sheet_name for table in tables), question)
    answers = []
    for table in tables:
        if named and table.sheet_name not in named:
            continue
        predicates = categorical_predicates(question, source_headers(question, table))
        if not predicates or len(predicates) > 8:
            continue
        filters = []
        for column, (kind, value), operator in predicates:
            if operator not in {"equals", "not_equals", "contains", "is_blank", "not_blank"}:
                break
            parsed = None if kind == "NoneType" else value == "true" if kind == "bool" else value
            if kind == "str":
                spellings = {match.group().casefold() for match in re.finditer(
                    r"(?<![a-z0-9_])" + r"\s+".join(map(re.escape, value.split())) + r"(?![a-z0-9_])",
                    question, re.I)}
                if len(spellings) != 1:
                    break
                parsed = next(iter(spellings))
            filters.append(TabularFilter(column_id=column, operator=operator, value=parsed))
        if len(filters) != len(predicates):
            continue
        plan = TabularQueryPlan(operation="row_count", table_id=table.id, filters=filters)
        if not count_scope_covered(question, plan, table):
            continue
        if answer := execute_tabular_query(plan, summary, index, question):
            answers.append(answer)
    # Same words in multiple tables do not justify choosing whichever was first.
    return answers[0] if len(answers) == 1 else None


def checked_legacy_count(question, found, summary, index):
    if summary is None or index is None:
        return None
    answers = []
    for table in build_query_tables(summary):
        matching = [column.id for column in table.columns
                    if column.header_reference == found.get("header_reference")]
        if len(matching) != 1 or len(table.rows) != found.get("count"):
            continue
        plan = TabularQueryPlan(operation="row_count", table_id=table.id, column_ids=matching)
        if not count_scope_covered(question, plan, table):
            continue
        if answer := execute_tabular_query(plan, summary, index, question):
            answers.append(answer)
    return answers[0] if len(answers) == 1 else None
