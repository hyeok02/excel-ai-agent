"""Explicit arithmetic mean across stored observations, not per-period resampling."""
from decimal import Decimal, localcontext
import re

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from app.agent.query.resampled_trend_calculations import calculate_bucket, complete_bucket
from app.agent.query.trend_date_bounds import parse_trend_date_bounds, select_trend_periods
from app.agent.query.trend_request import trend_request_error
from app.agent.query.trend_selection import scoped_trend_candidates, prepare_trend_candidate, distinct_trend_candidates
from app.agent.query.trend_sources import trend_candidates
from app.agent.query.trend_render import _value
from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.grouped_trend_request_spans import erase_spans, headers_for
from app.agent.query.tabular_catalog import build_query_tables

_AVERAGE = re.compile(r"(?:단순|산술)\s*평균(?:은|을|이|의)?|\b(?:simple|arithmetic)\s+(?:mean|average)\b", re.I)
_OBSERVED = re.compile(r"(?<![가-힣])(?:관측값|저장값|값)(?:들의|의|을|은)?|저장된|기록된|\b(?:observed|stored)\s+values?\b", re.I)


def observed_series_average(question, summary, index):
    if not _AVERAGE.search(question):
        return None
    protected = [match.span() for table in build_query_tables(summary) for _, match in headers_for(question, table)]
    average = [match.span() for match in _AVERAGE.finditer(question)
               if not any(start <= match.start() < end for start, end in protected)]
    if not average:
        return None
    spans = average + [match.span() for match in _OBSERVED.finditer(question)
                       if not any(start <= match.start() < end for start, end in protected)]
    clean = erase_spans(question, spans)
    candidates, named = scoped_trend_candidates(clean, trend_candidates(summary, index, clean), summary)
    if not candidates:
        return None
    prepared = [prepare_trend_candidate(item, index.rows) for item in candidates]
    valid = distinct_trend_candidates([(item, units) for item, units in prepared if not item.error])
    if len(valid) != 1 or any(item.error for item, _ in prepared):
        return _unavailable(question, "평균을 계산할 원본 시계열을 하나로 확정하지 못했습니다. 날짜·누락값·대상 범위를 확인해 주세요.")
    candidate, units = valid[0]
    if error := trend_request_error(clean + " 추이", candidate.observations, named):
        return _unavailable(question, error)
    bounds, error = parse_trend_date_bounds(clean, candidate.observations, named)
    if error:
        return _unavailable(question, error)
    points = select_trend_periods(candidate.observations, bounds)
    if len(points) < 2:
        return _unavailable(question, "요청한 기간에 평균을 계산할 관측값이 두 개 이상 필요합니다.")
    if len({unit.identity for unit in units}) != 1:
        return _unavailable(question, "서로 다른 단위의 원본 값을 한 평균으로 계산하지 않았습니다.")
    try:
        value = calculate_bucket(points, "average")
        spec = parse_number_format(points[0].value.number_format)
        if spec.mode not in {"", "raw"}:
            raise ValueError("날짜·시간 값은 숫자의 평균으로 계산하지 않았습니다.")
        with localcontext() as context:
            context.prec = max(60, value.adjusted() + 20)
            display = value.quantize(Decimal("0.000001"))
        rendered = _value(display, spec, units[0])
    except (ValueError, TypeError, ArithmeticError) as error:
        return _unavailable(question, str(error) or "관측값 평균을 원본과 대조하지 못했습니다.")
    limitations = []
    if not all(unit.known for unit in units):
        limitations.append("원본 저장값의 단위는 확정하지 못했습니다.")
    grain = points[0].grain
    if grain in {"month", "quarter", "annual"} and not complete_bucket(
            points, bounds.start or points[0].period, bounds.end or points[-1].period, grain, "average"):
        limitations.append("요청 기간의 일부 관측 시점이 없습니다. 기록된 값만의 평균이며 전체 기간 평균으로 확정하지 않았습니다.")
    if candidate.hidden_rows:
        limitations.append("숨겨진 행을 제외한 표시 데이터의 평균입니다.")
    references = [*candidate.context]
    for point in points:
        references.extend((point.label, point.period_cell, point.value, *point.context_cells, *point.entity_cells))
    for unit in units:
        references.extend(unit.references)
    label = str(points[0].label.value)
    text = (f"원본 범위: {candidate.table_id}\n{bounds.note}\n"
            f"{label}: {points[0].period.date()} ~ {points[-1].period.date()}의 "
            f"원본 관측값 {len(points)}개 단순 평균은 {'약 ' if display != value else ''}{rendered}입니다.\n"
            "계산: 해당 관측값의 합계 ÷ 관측값 개수. 날짜별로 다시 묶은 평균이나 가중평균이 아닙니다.")
    return QuestionAnswer(question=question, answer=text, status="limited" if limitations else "answered",
        confidence=0.9 if limitations else 1, selected_tools=["observed_series_average"],
        evidence=[_evidence(cell) for cell in dict.fromkeys(references)], limitations=limitations,
        verification=QuestionAnswerVerification(level="source_checked" if limitations else "request_checked",
            checks=["table_scope", "metric", "source_values", "complete_series", "chronological_order",
                    "explicit_observation_average", "calculation"] + ([] if limitations else ["request_alignment", "unit"])))


def _unavailable(question, reason):
    return QuestionAnswer(question=question, answer=reason, status="insufficient_evidence", confidence=0,
                          selected_tools=["observed_series_average"], evidence=[], limitations=[reason])
