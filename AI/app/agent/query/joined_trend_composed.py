"""Route proven joined cells through the common derived/resampling engines."""
from dataclasses import replace
import re

from app.agent.query.derived_trend_request import GROWTH, SHARE, calculation_question
from app.agent.query.grouped_share_trend_request import protect_headers, restore_headers
from app.agent.query.grouped_trend_request import GroupedTrendRequest, parse_grouped_request
from app.agent.query.grouped_trend_scope import scoped_records
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.scoped_derived_request import _protect_values


def composed_joined_answer(question, source, named, index, summary):
    clean, masked = _clean_joined_question(source)
    if GROWTH.search(masked) or SHARE.search(masked):
        from app.agent.query.scoped_derived_answers import scoped_derived_from_source
        request = parse_grouped_request(clean, source.table, source.records, source.metric.id, source.date.id)
        request = request or GroupedTrendRequest((), (), None, clean, "")
        result = scoped_derived_from_source(source.source_question, replace(source, request=request), named, index, summary=None)
        if result is not None:
            result.question = question
        return result
    from app.agent.query.resampled_trend_request import parse_resampled_request, resampling_source_question
    from app.agent.query.resampled_trend_answers import resampled_answer_from_source
    request = parse_resampled_request(source.source_question, summary, index)
    if request is None:
        return None
    parsed = parse_grouped_request(resampling_source_question(request), source.table, source.records,
                                   source.metric.id, source.date.id)
    selected, note, error = scoped_records(source.records, parsed, source.table,
                                          source.headers[source.metric.id], source.date.id, named)
    if error:
        raise ValueError("연결한 이력의 집계 기간을 확정하지 못했습니다: " + error)
    if not selected:
        raise ValueError("요청한 조건·집계 기간에 해당하는 연결 이력이 없습니다.")
    source = replace(source, request=parsed, records=tuple(selected), note=note)
    return resampled_answer_from_source(question, source, index, request, named)


def _clean_joined_question(source):
    masked, fields = protect_headers(source.source_question, [source.table])
    values = [cell.value for row in source.records for cell in row.values()
              if isinstance(cell.value, str) and cell.value.strip() and source_period(cell.value) is None]
    masked, values = _protect_values(masked, values)
    clean = re.sub(r"안에서|내에서", "에서", calculation_question(masked))
    return restore_headers(restore_headers(clean, values), fields), masked
