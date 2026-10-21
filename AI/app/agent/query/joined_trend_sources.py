"""Build a typed many-to-one source view without inventing spreadsheet cells."""
from dataclasses import dataclass, replace

from app.agent.query.grouped_trend_request import GroupedTrendRequest, parse_grouped_request
from app.agent.query.grouped_trend_request_spans import headers_for
from app.agent.query.grouped_trend_sources import GroupedSource
from app.agent.query.joined_trend_binding import selected_tables, stripped_join_question, _key_mentioned
from app.agent.query.joined_trend_population import select_left_population
from app.agent.query.joined_trend_roles import bind_joined_roles
from app.agent.query.metric_observation_cells import _DATE_HEADER
from app.agent.query.relational_join import joined_rows
from app.agent.query.relational_models import RelationalQueryPlan, RelationalKey
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_catalog_models import QueryTable


@dataclass(frozen=True)
class JoinedSource(GroupedSource):
    source_question: str = ""
    join_note: str = ""
    explicit_keys: bool = False
    metadata_dates: tuple[str, ...] = ()


def joined_trend_sources(question, summary, index):
    tables = build_query_tables(summary)
    selected, named = selected_tables(question, tables)
    left, right, metric, date, keys, sides, cells, headers, contexts = bind_joined_roles(question, selected, tables, index)
    redundant = {f"right.{column.id}" for _, column in keys}
    columns = tuple(replace(column, id=f"{side}.{column.id}") for side, table in sides.items()
                    for column in table.columns if f"{side}.{column.id}" not in redundant)
    combined_headers = {f"{side}.{key}": cell for side in sides for key, cell in headers[side].items()
                        if f"{side}.{key}" not in redundant}
    table = QueryTable(f"{left.id} + {right.id}", left.sheet_name, left.reference, columns, (), True)
    metric, date = replace(metric, id=f"left.{metric.id}"), replace(date, id=f"left.{date.id}")
    residual = stripped_join_question(question, list(sides.values()), keys)
    sides["left"] = select_left_population(residual, table, sides, cells, combined_headers, metric, date, named, summary, index)
    plan = RelationalQueryPlan(operation="row_list", left_table_id=left.id, right_table_id=right.id,
                               on=[RelationalKey(left_column_id=a.id, right_column_id=b.id) for a, b in keys])
    joined, unmatched, _ = joined_rows(plan, sides)
    if unmatched:
        raise ValueError(f"원본 이력 {unmatched}개 행의 연결 대상을 찾지 못했습니다. 이 행들을 임의로 빼고 추이를 계산하지 않았습니다.")
    if len(joined) > 20_000:
        raise ValueError("연결할 전체 이력이 검증 한도를 넘었습니다. 원본 표 범위나 조건을 좁혀 주세요.")
    records, evidence = [], []
    for row in joined:
        record = {f"{side}.{key}": cell for side in sides
                  for key, cell in cells[side][getattr(row, side).row_number].items()
                  if f"{side}.{key}" not in redundant}
        records.append(record)
        evidence.extend(cells[side][getattr(row, side).row_number][column.id]
                        for pair in keys for side, column in zip(("left", "right"), pair))
    evidence.extend(headers[side][column.id] for pair in keys for side, column in zip(("left", "right"), pair))
    request = parse_grouped_request(residual, table, records, metric.id, date.id)
    request = request or GroupedTrendRequest((), (), None, residual, "")
    # Equality keys are structural provenance, not hidden grouping dimensions.
    # Preserve a key in the schema if the user actually groups/filters by it.
    used = {*request.groups, *(item.column_id for item in request.filters)}
    removable = {f"left.{a.id}" for a, _ in keys} - used
    mentioned = {key for key, _ in headers_for(question, right)}
    unused_dates = [column for column in right.columns if _DATE_HEADER.search(column.header)
                    and column.id not in mentioned and f"right.{column.id}" not in used | redundant]
    for column in unused_dates:
        key = f"right.{column.id}"
        removable.add(key)
        evidence.append(combined_headers[key])
        evidence.extend(record[key] for record in records if key in record)
    table = replace(table, columns=tuple(column for column in columns if column.id not in removable))
    combined_headers = {key: cell for key, cell in combined_headers.items() if key not in removable}
    key_note = "연결 기준: " + "; ".join(f"{left.sheet_name}.{a.header} = {right.sheet_name}.{b.header}" for a, b in keys)
    key_note += f"\n추이 날짜 축: {left.sheet_name}.{date.header}"
    source = JoinedSource(table, metric, date, tuple(records), combined_headers,
                          tuple(contexts), 0, request, source_question=residual, join_note=key_note,
                          explicit_keys=all(_key_mentioned(a.header, question) for a, _ in keys),
                          metadata_dates=tuple(f"{right.sheet_name}.{column.header}" for column in unused_dates))
    return source, named, tuple(dict.fromkeys(evidence))
