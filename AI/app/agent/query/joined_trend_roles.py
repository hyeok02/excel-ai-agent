"""Choose a fact date/measure only after excluding bound join dimensions."""
from app.agent.query.grouped_trend_conditions import categorical_conditions
from app.agent.query.grouped_trend_request_spans import grouping_spans, headers_for
from app.agent.query.joined_trend_binding import bind_keys
from app.agent.query.joined_trend_readback import read_join_side
from app.agent.query.metric_observation_cells import _DATE_HEADER
from app.agent.query.trend_labels import trend_column_matches


def bind_joined_roles(question, selected, tables, index):
    loaded = {table.id: read_join_side(table, tables, index, question) for table in selected}
    keys = bind_keys(question, selected[0], selected[1])
    options = []
    for position, table in enumerate(selected):
        table, records, _, _ = loaded[table.id]
        headers = headers_for(question, table)
        groups, _ = grouping_spans(question, headers)
        dates = [column for column in table.columns if _DATE_HEADER.search(column.header)]
        conditions, _ = categorical_conditions(question, table, list(records.values()), headers,
                                                "__metric__", "__date__")
        dimensions = {*groups, *(column.id for column in dates),
                      *(pair[position].id for pair in keys), *(item.column_id for item in conditions)}
        metrics = [column for column in table.columns if column.id not in dimensions
                   and trend_column_matches(column, question)]
        if not metrics:
            continue
        named_dates = [column for column in dates if any(key == column.id for key, _ in headers)]
        if len(named_dates) == 1:
            dates = named_dates
        if len(metrics) != 1 or len(dates) != 1:
            raise ValueError("연결 추이의 날짜 열과 수치 열을 하나로 확정하지 못했습니다. 원본 열 이름을 지정해 주세요.")
        options.append((position, table, metrics[0], dates[0]))
    if len(options) != 1:
        raise ValueError("연결 추이의 원본 수치가 여러 표에 있거나 확인되지 않습니다. 대상 수치 열과 날짜 축을 지정해 주세요.")
    position, left, metric, date = options[0]
    right = selected[1 - position]
    keys = keys if position == 0 else [(right_key, left_key) for left_key, right_key in keys]
    sides, cells, headers, contexts = {}, {}, {}, []
    for side, table in (("left", left), ("right", right)):
        sides[side], cells[side], headers[side], context = loaded[table.id]
        contexts.extend(context)
    return left, right, metric, date, keys, sides, cells, headers, contexts
