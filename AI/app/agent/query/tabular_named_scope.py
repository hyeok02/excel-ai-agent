"""Narrow a whole-table frequency plan to the columns the question names.

"사건 발생일(Key Development Date) 분포를 항목별로 요약해줘" asks for one column's
distribution; "항목별로" is the answer's layout, not a request for every column.
Only full source headers written in the question narrow the plan, so a request
naming no column (a checklist summary) keeps its whole-table scope.
"""
import re

from app.agent.query.ambiguity_labels import mentioned_sources
from app.agent.query.tabular_request_scope import header_request_text


def named_column_scope(question, plan, table, tables):
    if plan.operation != "frequencies" or plan.column_scope != "all_attributes":
        return plan
    named = named_columns(question, table, tables, skipped=plan.identity_column_ids)
    if not named:
        return plan
    return plan.model_copy(update={
        "column_scope": "selected", "column_ids": [column.id for column in named], "identity_column_ids": [],
    })


def named_columns(question, table, tables, skipped=()):
    """Visible columns whose whole header the question writes; a header inside a longer named one is dropped."""
    text = header_request_text(question, mentioned_sources((item.sheet_name for item in tables), question))
    skipped = set(skipped) | set(getattr(table, "hidden_columns", ()))
    named = [column for column in table.columns if column.id not in skipped
             and len(_normal(column.header)) >= 4 and _mentioned(column.header, text)]
    return [column for column in named if not any(
        _normal(column.header) != _normal(other.header) and _normal(column.header) in _normal(other.header)
        for other in named)]


def _mentioned(header, text):
    """The whole header as a name: 'Type' inside 'Key Development Type & Category' is not it."""
    for match in re.finditer(re.escape(_normal(header)), text):
        before = re.sub(r"[\s&/,+-]+$", "", text[:match.start()])
        after = re.sub(r"^[\s&/,+-]+", "", text[match.end():])
        if not re.search(r"[a-z0-9]$", before) and not re.match(r"[a-z0-9]", after):
            return True
    return False


def _normal(value):
    return re.sub(r"\s+", " ", str(value).casefold()).strip()
