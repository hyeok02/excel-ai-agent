"""Source-verified calendar aggregation, including conditional/grouped inputs."""
from dataclasses import replace
import re

from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope
from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.grouped_trend_series import grouped_series
from app.agent.query.grouped_trend_sources import grouped_sources
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from app.agent.query.resampled_trend_calculations import LABELS, OPERATIONS, resample_candidate, missing_bucket_scope
from app.agent.query.resampled_trend_request import parse_resampled_request, resampling_source_question
from app.agent.query.trend_render import _value, render_trend
from app.agent.query.trend_request import trend_request_error


def resampled_trend_answer(question, summary, index):
    try:
        request = parse_resampled_request(question, summary, index)
        if request is None:
            return None
        sources, named = grouped_sources(resampling_source_question(request), summary, index)
        if len(sources) != 1:
            raise ValueError("기간별로 집계할 날짜·지표·원본 표를 하나로 확정하지 못했습니다. 시트·표 범위와 지표를 지정해 주세요.")
        return resampled_answer_from_source(question, sources[0], index, request, named)
    except (ValueError, TypeError, ArithmeticError) as error:
        return resampling_unavailable(question, str(error) if isinstance(error, ValueError)
                                      else "기간별 집계 계산을 원본과 대조하지 못했습니다.")


def resampled_answer_from_source(question, source, index, request, named=()):
    """Reusable by a verified join adapter; no synthetic values become evidence."""
    source = replace(source, request=replace(source.request, statistic=None))
    series = grouped_series(source, index, allow_single_period=True)
    parts = [f"원본 범위: {source.table.id}", source.note,
             f"계산: 달력 기준 {LABELS[request.grain]} {OPERATIONS[request.statistic]}. "
             "원본에 기록된 관측값만 계산하며, 없는 날짜는 0이나 보간값으로 채우지 않습니다."]
    description = re.sub(r"(?:; )?각 시점 집계: \w+", "", source.request.description)
    if description:
        parts.append(description)
    references, limitations, all_buckets, all_units, contexts = [], [], [], [], set()
    for title, candidate, units, cells in series:
        _, residual = bind_explicit_metric_scope(source.request.residual, candidate.observations)
        if residual != source.request.residual:
            residual = re.sub(r"범위(?:에서|의|내)?|\brange\b", " ", residual, flags=re.I)
        if error := trend_request_error(residual, candidate.observations, named):
            raise ValueError(error)
        buckets = resample_candidate(candidate, units, request)
        contexts.update((point.grain, point.scenario) for point in candidate.observations)
        if len(buckets) > 100:
            raise ValueError("표시·검증할 기간이 100개를 초과했습니다. 날짜 범위를 좁혀 주세요.")
        lines = [title] if title else []
        spec = parse_number_format(candidate.observations[0].value.number_format)
        for bucket in buckets:
            originals = bucket.observations
            bounds = f"{originals[0].period.date()}~{originals[-1].period.date()}"
            text = _value(bucket.point.value.value, spec, units[0])
            lines.append(f"- {bucket.label}: {text} (원본 관측값 {len(originals)}개, {bounds})")
        if len(buckets) >= 2:
            lines.append(render_trend(tuple(bucket.point for bucket in buckets), tuple(units[0] for _ in buckets)))
        parts.append("\n".join(lines))
        if any(not bucket.complete for bucket in buckets):
            limitations.append("기간 끝의 실제 관측일을 확인해 주세요. 마지막 저장값이며 달력상 기말값으로 확정하지 않았습니다."
                               if request.statistic == "last" else
                               "일부 기간의 달력상 전체 관측값을 확인하지 못했습니다. 표시된 값은 기록된 관측값만의 집계이며 전체 기간 집계로 확정하지 않았습니다.")
        if missing_bucket_scope(buckets, request, residual, candidate.observations, named):
            limitations.append("조회 범위 중 원본 관측값이 전혀 없는 기간이 있습니다. 해당 기간을 0으로 가정하거나 누락 없이 이어진 추이로 확정하지 않았습니다.")
        references.extend(cells)
        all_units.extend(units)
        all_buckets.append(buckets)
    if not all(unit.known for unit in all_units):
        limitations.append("원본 수치의 단위를 확정하지 못했습니다.")
    if len({unit.identity for unit in all_units}) != 1:
        limitations.append("그룹별 단위가 달라 동일 단위의 비교로 확정하지 않았습니다.")
    if len(contexts) > 1:
        limitations.append("그룹별 원본 관측 주기·실적/예상 구분이 달라 동일 기준의 비교로 확정하지 않았습니다.")
    if len({tuple(bucket.start for bucket in buckets) for buckets in all_buckets}) > 1:
        limitations.append("그룹별 관측 기간이 다릅니다. 없는 기간을 0으로 채우지 않았습니다.")
    if source.hidden:
        limitations.append("숨겨진 행을 제외한 표시 데이터만 집계했습니다.")
    if request.statistic == "average":
        parts.append("평균은 저장된 관측값의 단순평균입니다. 가중평균이나 관측되지 않은 날짜를 포함한 평균이 아닙니다.")
    return QuestionAnswer(question=question, answer="\n\n".join(part for part in parts if part),
        status="limited" if limitations else "answered", confidence=0.9 if limitations else 1,
        selected_tools=["chronological_trend", "resampled_trend"], limitations=list(dict.fromkeys(limitations)),
        evidence=[_evidence(cell) for cell in dict.fromkeys(references)],
        verification=QuestionAnswerVerification(level="source_checked" if limitations else "request_checked",
            checks=["table_scope", "complete_series", "source_values", "filters", "grouping", "calendar_buckets",
                    "explicit_temporal_aggregation", "calculation", "chronological_order"]
                   + ([] if limitations else ["request_alignment", "unit", "complete_periods"])))


def resampling_unavailable(question, reason):
    return QuestionAnswer(question=question, answer=reason, status="insufficient_evidence", confidence=0,
                          selected_tools=["resampled_trend"], evidence=[], limitations=[reason])
