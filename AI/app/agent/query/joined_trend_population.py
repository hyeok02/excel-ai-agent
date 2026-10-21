"""Narrow detail rows only when predicates prove their scope before joining."""
from dataclasses import replace

from app.agent.query.joined_trend_bounds import derived_left_population
from app.agent.query.grouped_trend_request import GroupedTrendRequest, parse_grouped_request
from app.agent.query.grouped_trend_scope import scoped_records


def select_left_population(question, table, sides, cells, headers, metric, date, named, summary=None, index=None):
    derived = derived_left_population(question, table, sides, cells, headers, metric, date, named, index)
    if derived is not None:
        return derived
    if summary is not None:
        from app.agent.query.resampled_trend_request import parse_resampled_request, resampling_source_question
        resampling = parse_resampled_request(question, summary, index)
        if resampling:
            question = resampling_source_question(resampling)
    samples = [{f"{side}.{key}": cell for key, cell in record.items()}
               for side in sides for record in cells[side].values()]
    request = parse_grouped_request(question, table, samples, metric.id, date.id)
    request = request or GroupedTrendRequest((), (), None, question, "")
    request = replace(request, groups=(), filters=tuple(condition for condition in request.filters
                                                      if condition.column_id.startswith("left.")))
    records = [{f"left.{key}": cell for key, cell in record.items()} for record in cells["left"].values()]
    selected, _, error = scoped_records(records, request, table, headers[metric.id], date.id, named)
    if error:
        raise ValueError("연결 전 이력의 날짜 범위를 확정하지 못했습니다: " + error)
    # A relative date anchor must follow the final right-side population. Only
    # absolute calendar scopes may safely exclude unjoined detail rows here.
    from app.agent.query.trend_relative_dates import RELATIVE_CUE
    if RELATIVE_CUE.search(request.residual):
        return sides["left"]
    row_numbers = {int(row[date.id].address.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")) for row in selected}
    return replace(sides["left"], rows=tuple(row for row in sides["left"].rows if row.row_number in row_numbers))
