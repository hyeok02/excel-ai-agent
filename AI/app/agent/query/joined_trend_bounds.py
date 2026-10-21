"""Prejoin calendar windows include every required derived baseline date."""
from dataclasses import replace

from app.agent.query.derived_trend_request import GROWTH, SHARE, derived_request, calculation_question
from app.agent.query.grouped_share_trend_request import protect_headers, restore_headers
from app.agent.query.grouped_trend_request import GroupedTrendRequest, parse_grouped_request
from app.agent.query.grouped_trend_scope import scoped_records
from app.agent.query.grouped_trend_sources import GroupedSource
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.scoped_derived_request import _protect_values
from app.agent.query.scoped_derived_sources import expanded_growth_source
from app.agent.query.trend_relative_dates import RELATIVE_CUE


def derived_left_population(question, table, sides, cells, headers, metric, date, named, index):
    masked, fields = protect_headers(question, [table])
    values = [cell.value for side in cells for row in cells[side].values() for cell in row.values()
              if isinstance(cell.value, str) and cell.value.strip() and source_period(cell.value) is None]
    masked, literals = _protect_values(masked, values)
    growth, share = bool(GROWTH.search(masked)), bool(SHARE.search(GROWTH.sub(" ", masked)))
    if not growth and not share:
        return None
    if growth and share:
        return sides["left"]  # Final common operator validation rejects this.
    clean = restore_headers(restore_headers(calculation_question(masked), literals), fields)
    if RELATIVE_CUE.search(clean):
        return sides["left"]  # Final right-side filters define the date anchor.
    samples = [{f"{side}.{key}": cell for key, cell in record.items()}
               for side in sides for record in cells[side].values()]
    request = parse_grouped_request(clean, table, samples, metric.id, date.id)
    request = request or GroupedTrendRequest((), (), None, clean, "")
    # Categorical share targets cannot filter away their denominator population.
    filters = tuple(item for item in request.filters if item.column_id.startswith("left.")) if growth else ()
    request = replace(request, groups=(), filters=filters)
    records = tuple({f"left.{key}": cell for key, cell in record.items()} for record in cells["left"].values())
    source = GroupedSource(table, metric, date, records, headers, (), 0, request)
    if growth:
        operation, error = derived_request(masked + " 추이", (metric.header,))
        if error or operation is None or operation.basis == "previous":
            return sides["left"]  # Group-specific previous dates need the join.
        expanded, _ = expanded_growth_source(source, operation.basis, named, index, None)
        selected = expanded.records
    else:
        selected, _, error = scoped_records(records, request, table, headers[metric.id], date.id, named)
        if error:
            raise ValueError("비중 계산에 필요한 연결 이력 날짜를 확정하지 못했습니다: " + error)
    numbers = {int(row[date.id].address.lstrip("ABCDEFGHIJKLMNOPQRSTUVWXYZ")) for row in selected}
    return replace(sides["left"], rows=tuple(row for row in sides["left"].rows if row.row_number in numbers))
