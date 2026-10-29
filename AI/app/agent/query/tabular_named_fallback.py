"""When a model's distribution plan cannot be checked, count the column the question names.

The model may pick a wrong table ID, an ambiguous identity column or a kind that
does not fit; the question itself still names the source column by its full
header. Only one table may hold every named column, and the question may ask
nothing but that column's distribution (no condition, period or calculation);
otherwise the refusal stands.
"""
import re

from app.agent.query.ambiguity_labels import mentioned_sources
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_named_scope import named_columns
from app.agent.query.tabular_query_models import TabularQueryPlan


def named_frequency_answer(plan, summary, data_index, question):
    # The question decides, not the failed plan: GPT may have planned a row count,
    # a list or a lookup for the same distribution request.
    if plan is None:
        return None
    tables = build_query_tables(summary)
    sheets = mentioned_sources((table.sheet_name for table in tables), question)
    found = [(table, columns) for table in tables if not sheets or table.sheet_name in sheets
             if (columns := named_columns(question, table, tables))]
    if len(found) != 1:
        return None
    table, columns = found[0]
    if not _only_distribution(question, columns, sheets):
        return None
    named = TabularQueryPlan(operation="frequencies", table_id=table.id, column_ids=[column.id for column in columns])
    return execute_tabular_query(named, summary, data_index, question)


_DISTRIBUTION = frozenset({
    "분포", "구성", "항목별", "항목별로", "값별", "표시별", "종류별", "별", "별로", "건수", "개수", "현황", "요약",
    "요약해줘", "정리", "정리해줘", "알려줘", "보여줘", "말해줘", "줘", "해줘", "각", "값", "종류", "시트",
})
_PARTICLE = re.compile(r"(?:을|를|은|는|이|가|의|과|와|및|로|으로|에서)$")


def _only_distribution(question, columns, sheets):
    """Every word left after the column names (and a Korean gloss before them) asks for counts."""
    text = question.casefold()
    for name in sorted({str(column.header).casefold() for column in columns} | {s.casefold() for s in sheets},
                       key=len, reverse=True):
        text = re.sub(r"(?:[가-힣]+(?:\s+[가-힣]+){0,2}\s*)?\(\s*" + re.escape(name) + r"\s*\)", " ", text)
        text = text.replace(name, " ")
    words = re.findall(r"[가-힣]+|[a-z0-9]+", text)
    return all(word in _DISTRIBUTION or _PARTICLE.sub("", word) in _DISTRIBUTION | {""} for word in words)
