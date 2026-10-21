"""Bind two-table trend requests to explicit source names and exact key labels."""
import re

from app.agent.query.ambiguity_labels import mentioned_sources, normalize_label, _source_matches
from app.agent.query.grouped_trend_request_spans import erase_spans, headers_for
from app.agent.query.metric_request_coverage import _remove_source_phrase
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_literals import without_literals
from app.agent.query.tabular_request_categories import value_matches
from app.agent.query.tabular_request_scope import explicit_ranges
from app.agent.query.trend_request import asks_trend

JOIN = re.compile(r"연결(?:해서|하여|한|해|하고|해서는)?|결합(?:해서|하여|한|해)?|"
                  r"\b(?:join(?:ed|ing)?|link(?:ed|ing)?|merg(?:e|ed|ing))\b", re.I)


def asks_joined_trend(question, summary=None, index=None):
    if not JOIN.search(question):
        return False
    tables = build_query_tables(summary) if summary else ()
    operation = _operation_text(question, tables, index)
    return bool(JOIN.search(operation)) and (asks_trend(question) or bool(re.search(
        r"증감률|증가율|비중|비율|점유율|월별|분기별|연도별|월간|연간|"
        r"\b(?:growth|share|ratio|monthly|quarterly|yearly)\b", question, re.I)))


def selected_tables(question, tables):
    names = mentioned_sources((table.sheet_name for table in tables), question)
    ranges = explicit_ranges(question)
    selected = [table for table in tables if not names or table.sheet_name in names]
    if ranges:
        selected = [table for table in selected if (table.sheet_name, table.reference) in ranges]
        if len(selected) != len(ranges):
            raise ValueError("연결 추이는 확인한 전체 표 범위를 지정해야 합니다. 부분 범위를 전체로 대신하지 않았습니다.")
    if len(selected) != 2 or (names and names != {table.sheet_name for table in selected}):
        raise ValueError("연결할 원본 표 두 개를 하나씩 확정해야 합니다. 시트명 또는 전체 표 범위를 지정해 주세요.")
    return selected, names or {table.sheet_name for table in selected}


def bind_keys(question, left, right):
    pairs = [(a, b) for a in left.columns for b in right.columns
             if normalize_label(a.header) == normalize_label(b.header)]
    explicit = [(a, b) for a, b in pairs if _key_mentioned(a.header, question)]
    if explicit:
        pairs = explicit
    elif len(pairs) != 1:
        raise ValueError("두 표를 연결할 공통 키가 없거나 여러 개입니다. 양쪽에 있는 연결 열 이름을 지정해 주세요.")
    if len(pairs) > 4 or len({a.id for a, _ in pairs}) != len(pairs) or len({b.id for _, b in pairs}) != len(pairs):
        raise ValueError("연결 키가 중복되거나 너무 많습니다. 고유한 원본 연결 열을 지정해 주세요.")
    # Named unequal keys require an explicit mapping; guessing their pairing is
    # not supported. Unknown key names remain in residual and fail coverage.
    return pairs


def stripped_join_question(question, tables, keys):
    remaining = question
    for table in tables:
        remaining = _remove_source_phrase(remaining, table.sheet_name)
        remaining = remaining.replace(table.id, " ")
    for left, right in keys:
        for label in {left.header, right.header}:
            # Remove a key only at its explicit join-binding occurrence, not a
            # later grouping/filter using the same actual source column.
            pattern = re.escape(label) + r"\s*(?:을|를)?\s*(?:키로|기준으로|으로|로)"
            remaining = re.sub(pattern, " ", remaining, flags=re.I)
            remaining = re.sub(r"\b(?:on|using)\s+" + re.escape(label) + r"(?!\w)", " ", remaining, flags=re.I)
    operation = _operation_text(remaining, tables)
    remaining = erase_spans(remaining, [match.span() for match in JOIN.finditer(operation)])
    remaining = re.sub(r"\b(?:tables?|sheets?|with)\b|(?<!\w)(?:표|시트)(?:를|을)?(?!\w)", " ", remaining, flags=re.I)
    return remaining


def _operation_text(question, tables, index=None):
    protected = [match.span() for table in tables for _, match in headers_for(question, table)]
    protected.extend(match.span() for table in tables for match in _source_matches(table.sheet_name, question))
    for table in tables:
        values = {value for row in table.rows for value in row.values.values() if isinstance(value, str)}
        if index is not None:
            from app.agent.query.trend_source_readback import table_rows
            rows, _ = table_rows(table, tables, index, question)
            values.update(cell.value for row in rows for cell in row.cells if isinstance(cell.value, str))
        protected.extend(match.span() for value in values if JOIN.search(value)
                         for match in value_matches(question, value))
    return erase_spans(without_literals(question), protected)


def _key_mentioned(label, question):
    return bool(re.search(re.escape(label) + r"\s*(?:을|를)?\s*(?:키로|기준으로|으로|로)", question, re.I)
                or re.search(r"\b(?:on|using)\s+" + re.escape(label) + r"(?!\w)", question, re.I))
