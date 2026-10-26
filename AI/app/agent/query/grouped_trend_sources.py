"""Read complete source rectangles before binding any conditional trajectory."""
import re
from dataclasses import dataclass

from app.agent.query.ambiguity_labels import mentioned_sources
from app.agent.query.metric_observation_cells import _DATE_HEADER
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_request_scope import explicit_ranges, _inside
from app.agent.query.trend_labels import trend_column_matches
from app.agent.query.trend_source_context import verified_context
from app.agent.query.trend_source_readback import table_rows, column_cells
from app.agent.query.trend_source_scope import source_scope_names
from app.agent.query.grouped_trend_scope import scoped_records, filter_records
from app.agent.query.workbook_source import source_for


@dataclass(frozen=True)
class GroupedSource:
    table: object
    metric: object
    date: object
    records: tuple
    headers: dict
    context: tuple
    hidden: int
    request: object
    note: str = ""


def grouped_sources(question, summary, index):
    from app.agent.query.grouped_trend_request import parse_grouped_request
    tables = build_query_tables(summary)
    named = mentioned_sources((sheet.name for sheet in summary.sheets), question)
    ranges = explicit_ranges(question)
    sources, names = [], source_scope_names(index, question, tables)
    for table in tables:
        if named and table.sheet_name not in named:
            continue
        if ranges and not any(sheet == table.sheet_name and all(
                _inside(corner, reference) for corner in table.reference.split(":"))
                for sheet, reference in ranges):
            continue
        metrics = [column for column in table.columns if trend_column_matches(column, question)]
        if not metrics:
            continue
        rows, error = table_rows(table, tables, index, question)
        header_row = min((int(re.search(r"\d+$", c.header_reference)[0]) for c in table.columns), default=0)
        records = [column_cells(row) for row in rows if row.row_number > header_row and row.cells]
        dates = [c for c in table.columns if _DATE_HEADER.search(c.header)]
        if not dates:
            dates = [c for c in table.columns if sum(bool(source_period(row[c.id].value))
                     for row in records if c.id in row and isinstance(row[c.id].value, str)) >= 2]
        preliminary = parse_grouped_request(question, table, records, "__measure__",
                                            dates[0].id if len(dates) == 1 else "__date__")
        if preliminary is None:
            continue
        dimensions = {*preliminary.groups, *(date.id for date in dates)}
        dimensions.update(item.column_id for item in preliminary.filters if isinstance(item.value, str))
        metrics = [c for c in metrics if c.id not in dimensions]
        if not metrics:
            continue
        if len(dates) != 1:
            raise ValueError("요청 항목이 있는 표의 날짜 열이 없거나 여러 개입니다. 날짜 축이 명확한 표 범위를 지정해 주세요.")
        for metric in metrics:
            request = parse_grouped_request(question, table, records, metric.id, dates[0].id)
            if request is None:
                continue
            if error:
                raise ValueError("조건·그룹을 적용할 원본 표 전체를 확인하지 못했습니다. 일부 행만 집계하지 않았습니다.")
            captions = verified_context(table.context, index)
            cells = {cell.reference: cell for row in rows for cell in row.cells}
            headers = {c.id: cells.get(c.header_reference) for c in table.columns}
            if captions is None or any(cell is None for cell in headers.values()):
                raise ValueError("원본 표 머리글과 범위를 대조하지 못했습니다.")
            hidden = set(table.excluded_rows)
            provider = source_for(index)
            if provider:
                if table.sheet_name not in provider.authorized_sheets:
                    raise ValueError("접근 가능한 원본 시트 범위를 확인하지 못했습니다.")
                hidden.update(provider.sheet(table.sheet_name).hidden_rows)
            visible = [row for row in records if int(re.search(r"\d+$", next(iter(row.values())).address)[0]) not in hidden]
            selected, note, scope_error = scoped_records(visible, request, table, headers[metric.id], dates[0].id, names)
            if scope_error:
                raise ValueError("조건으로 선택한 행의 날짜 범위를 확정하지 못했습니다: " + scope_error)
            if not selected:
                raise ValueError("지정한 조건과 날짜 범위에 해당하는 원본 행이 없습니다.")
            sources.append(GroupedSource(table, metric, dates[0], tuple(selected), headers,
                                         tuple(captions), len(hidden), request, note))
    return sources, named
