"""Prove a categorical numerator and its complete same-table population."""
from dataclasses import replace
import re

from app.agent.query.derived_trend_request import SHARE, TEMPORAL
from app.agent.query.grouped_trend_sources import grouped_sources
from app.agent.query.trend_source_readback import table_rows, column_cells
from app.agent.query.trend_source_scope import scope_dated_items
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_categories import value_matches
from app.agent.query.grouped_share_trend_request import clean_share_question, whole_relation, remove_whole
from app.agent.query.metric_observation_cells import _numeric
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.trend_labels import trend_metric_label_matches


def category_share_source(question, summary, index):
    if not SHARE.search(question) or not TEMPORAL.search(question):
        return None
    tables = build_query_tables(summary)
    clean, operation = clean_share_question(question, tables)
    if not SHARE.search(operation) or not TEMPORAL.search(operation):
        return None
    requested = {column.header for table in tables for column in table.columns
                 if trend_metric_label_matches(column.header, question)
                 and any(_numeric(row.values.get(column.id)) for row in table.rows)}
    if len(requested) > 1:
        return None  # Explicit source-operand ratios use the derived adapter.
    sources, named = grouped_sources(clean, summary, index)
    # A two-metric share belongs to the ordinary derived-source handler.
    sources = [source for source in sources if source.request.filters]
    if not sources:
        if any(value_matches(operation, value) for table in tables for row in table.rows
               for value in row.values.values() if isinstance(value, str) and source_period(value) is None):
            raise ValueError("대상 범주와 전체 범위의 완전한 원본을 확인하지 못했습니다.")
        return None
    if len(sources) != 1:
        raise ValueError("비중의 원본 표·수치 열·대상 범주가 여러 개입니다. 원본 이름을 구체적으로 지정해 주세요.")
    source = sources[0]
    request = source.request
    for target in request.filters:
        for match in reversed(value_matches(operation, target.value)):
            operation = operation[:match.start()] + " " + operation[match.end():]
    if not SHARE.search(operation):
        return None
    if len(request.filters) != 1 or request.filters[0].operator != "equals" or request.groups or request.statistic:
        raise ValueError("범주 비중은 전체 표 중 하나의 범주를 지정해 주세요. 다른 조건이나 집계로 분모를 바꾸지 않았습니다.")
    target = request.filters[0]
    if not isinstance(target.value, str) or target.column_id in {source.metric.id, source.date.id}:
        raise ValueError("비중의 분자에 해당하는 범주 열과 값을 확정하지 못했습니다.")
    whole_relation(question, source, target)
    if source.hidden:
        raise ValueError("숨겨진 행이 있어 전체 범주의 합계를 분모로 검증하지 못했습니다.")
    rows, error = table_rows(source.table, tables, index, clean)
    if error:
        raise ValueError("비중 분모를 계산할 원본 표 전체를 확인하지 못했습니다.")
    header_row = max(int(re.search(r"\d+$", cell.address)[0]) for cell in source.headers.values())
    records = [column_cells(row) for row in rows if row.row_number > header_row and row.cells]
    residual = remove_whole(request.residual, source.table)
    records, note, error = scope_dated_items(
        residual, source.headers[source.metric.id], [(row, row.get(source.date.id)) for row in records],
        source.context, source_names=(*named, source.table.sheet_name))
    if error or not records:
        raise ValueError("전체 범주의 날짜 범위를 확인하지 못했습니다: " + (error or "빈 범위"))
    request = replace(request, filters=(), groups=(target.column_id,), residual=residual)
    return replace(source, request=request, records=tuple(records), note=note), target, named
