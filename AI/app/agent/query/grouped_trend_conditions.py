"""Derive conjunctive predicates from actual source labels and literal values."""
import re

from app.agent.query.grouped_trend_request_spans import adjacent_headers, with_tail
from app.agent.query.tabular_query_models import TabularFilter
from app.agent.query.tabular_request_categories import value_matches
from app.agent.query.tabular_request_numeric import _PREFIX, _SUFFIX, _PERCENT_EQUALS, _OPS
from app.agent.query.tabular_request_predicates import local_operator
from app.agent.query.tabular_request_literals import _LITERAL


def categorical_conditions(question, table, records, headers, metric_id, date_id):
    matches = []
    for column in table.columns:
        if column.id in {metric_id, date_id}:
            continue
        values = {cell.value for row in records if (cell := row.get(column.id)) is not None
                  and isinstance(cell.value, str) and cell.value.strip()}
        for value in values:
            for match in value_matches(question, value):
                if not any(header.start() <= match.start() and match.end() <= header.end()
                           for _, header in headers):
                    matches.append((column.id, value, match))
    matches = [item for item in matches if not any(
        other[2].start() <= item[2].start() and item[2].end() <= other[2].end()
        and len(other[1]) > len(item[1]) for other in matches)]
    by_span = {}
    for column, value, match in matches:
        by_span.setdefault(match.span(), []).append((column, value, match))
    filters, spans = [], []
    for (start, end), candidates in by_span.items():
        adjacent = adjacent_headers(question, start, end,
                                    [(key, header) for key, header in headers if key not in {metric_id, date_id}])
        if adjacent:
            named = {column for column, _ in adjacent}
            candidates = [item for item in candidates if item[0] in named]
        if len({column for column, _, _ in candidates}) != 1:
            raise ValueError("조건 값이 어느 원본 열을 뜻하는지 확정하지 못했습니다. 열 이름을 함께 지정해 주세요.")
        column, value, _ = candidates[0]
        operator = local_operator(question, start, end, headers)
        filters.append(TabularFilter(column_id=column, operator=operator, value=value))
        spans.append(with_tail(question, (start, end)))
        spans.extend(with_tail(question, header.span()) for key, header in adjacent if key == column)
    return filters, spans


def numeric_conditions(question, headers):
    filters, spans = [], []
    protected = [match.span() for _, match in headers] + [match.span() for match in _LITERAL.finditer(question)]
    for pattern in (_SUFFIX, _PREFIX, _PERCENT_EQUALS):
        for match in pattern.finditer(question):
            if any(start <= match.start() and match.end() <= end for start, end in protected):
                continue
            if any(start <= match.start() and match.end() <= end for start, end in spans):
                continue
            before = [(column, header) for column, header in headers if header.end() <= match.start()
                      and re.fullmatch(r"\s*(?:이|가|은|는|값|의)?\s*", question[header.end():match.start()])]
            if len({column for column, _ in before}) != 1:
                raise ValueError("숫자 조건을 적용할 원본 열을 확정하지 못했습니다. 열 이름과 조건을 함께 지정해 주세요.")
            column, _ = before[0]
            operation = _OPS[" ".join((match.groupdict().get("op") or "=").casefold().split())]
            raw = match.group("number").replace(",", "")
            value = float(raw) if "." in raw else int(raw)
            if not (-float("inf") < value < float("inf")):
                raise ValueError("숫자 조건은 유한한 값이어야 합니다.")
            filters.append(TabularFilter(column_id=column, operator=operation, value=value,
                                         value_unit="percent" if match.group("unit") else "raw"))
            spans.append(with_tail(question, match.span()))
    return filters, spans
