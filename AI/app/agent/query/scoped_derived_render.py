"""Render composite calculations with unchanged original-cell evidence only."""
import re

from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from app.agent.query.trend_request import trend_request_error


def validate_request(source, series, named):
    for _, candidate, _, _ in series:
        _, residual = bind_explicit_metric_scope(source.request.residual, candidate.observations)
        if residual != source.request.residual:
            residual = re.sub(r"범위(?:에서|의|내)?|\brange\b", " ", residual, flags=re.I)
        if error := trend_request_error(residual, candidate.observations, named):
            raise ValueError(error)


def composite_answer(question, source, parts, series, checks):
    units = [unit for _, _, group_units, _ in series for unit in group_units]
    limitations = []
    if not all(unit.known for unit in units):
        limitations.append("원본 저장값으로 계산했으나 수량·통화 단위까지는 확인하지 못했습니다.")
    if len({unit.identity for unit in units}) > 1:
        limitations.append("그룹별 단위가 달라 동일 단위의 비교로 확인하지 않았습니다.")
    if len({tuple(point.period for point in candidate.observations) for _, candidate, _, _ in series}) > 1:
        limitations.append("그룹별 원본 날짜가 다르므로 동일 기간의 비교로 확인하지 않았습니다.")
    if len({(point.grain, point.scenario) for _, candidate, _, _ in series for point in candidate.observations}) > 1:
        limitations.append("그룹별 관측 주기·실적/예상 기준이 달라 동일 기준의 비교로 확인하지 않았습니다.")
    references = tuple(dict.fromkeys(cell for _, _, _, cells in series for cell in cells))
    return QuestionAnswer(question=question, answer="\n\n".join([
        source.request.description, *parts]), status="limited" if limitations else "answered",
        confidence=0.85 if limitations else 1, selected_tools=["chronological_trend", "scoped_derived_trend"],
        evidence=[_evidence(cell) for cell in references], limitations=limitations,
        verification=QuestionAnswerVerification(level="source_checked" if limitations else "request_checked",
            checks=["table_scope", "metric", "filters", "grouping", "complete_series", "source_values",
                    "chronological_order", "calculation", "positive_denominator", "operand_lineage", *checks]
                   + ([] if limitations else ["unit", "request_alignment", "aligned_periods", "aligned_entity_scope"])))
