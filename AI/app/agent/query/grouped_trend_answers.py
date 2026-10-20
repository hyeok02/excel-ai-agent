"""Source-bound conditional/grouped trajectories, with no model or file rules."""
import re

from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope
from app.agent.query.grouped_trend_sources import grouped_sources
from app.agent.query.grouped_trend_series import grouped_series
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from app.agent.query.trend_request import trend_request_error
from app.agent.query.trend_render import render_trend


def grouped_trend_answer(question, summary, index):
    try:
        sources, named = grouped_sources(question, summary, index)
        if not sources:
            return None
        if len(sources) != 1:
            raise ValueError("조건·그룹 추이의 대상 표 또는 지표가 여러 개입니다. 시트·표 범위와 지표를 지정해 주세요.")
        source = sources[0]
        series = grouped_series(source, index)
        for _, candidate, _, _ in series:
            _, residual = bind_explicit_metric_scope(source.request.residual, candidate.observations)
            if residual != source.request.residual:
                residual = re.sub(r"범위(?:에서|의|내)?|\brange\b", " ", residual, flags=re.I)
            if error := trend_request_error(residual, candidate.observations, named):
                raise ValueError(error)
        return _answer(question, source, series)
    except (ValueError, TypeError, ArithmeticError) as error:
        reason = str(error) if isinstance(error, ValueError) else "조건·그룹 시계열 계산을 원본과 대조하지 못했습니다."
        return QuestionAnswer(question=question, answer=reason, status="insufficient_evidence", confidence=0,
                              selected_tools=["chronological_trend"], limitations=[reason], evidence=[])


def _answer(question, source, series):
    parts = [f"원본 범위: {source.table.id}", source.request.description]
    if source.note:
        parts.append(source.note)
    references, limitations = [], []
    for title, candidate, units, cells in series:
        parts.append((title + "\n" if title else "") + render_trend(candidate.observations, units))
        references.extend(cells)
    units = [unit for _, _, group_units, _ in series for unit in group_units]
    if not all(unit.known for unit in units):
        limitations.append("수치는 원본 저장값 기준이며 통화·수량 단위까지는 확정하지 못했습니다.")
    if len({unit.identity for unit in units}) > 1:
        limitations.append("그룹별 단위가 달라 같은 단위의 비교로 확정하지 않았습니다.")
    grids = {tuple(point.period for point in candidate.observations) for _, candidate, _, _ in series}
    if len(grids) > 1:
        limitations.append("그룹별 원본 관측 날짜가 다릅니다. 없는 시점은 0이나 보간값으로 채우지 않았습니다.")
    if len({(point.grain, point.scenario) for _, candidate, _, _ in series for point in candidate.observations}) > 1:
        limitations.append("그룹별 관측 주기·실적/예상 구분이 달라 동일 기준의 비교로 확정하지 않았습니다.")
    if source.hidden:
        limitations.append(f"숨겨진 {source.hidden}개 행을 제외한 표시 데이터의 추이입니다.")
    return QuestionAnswer(
        question=question, answer="\n\n".join(part for part in parts if part),
        status="limited" if limitations else "answered", confidence=0.9 if limitations else 1,
        selected_tools=["chronological_trend", "grouped_trend"], limitations=limitations,
        evidence=[_evidence(cell) for cell in dict.fromkeys(references)],
        verification=QuestionAnswerVerification(level="source_checked" if limitations else "request_checked",
            checks=["table_scope", "complete_series", "source_values", "filters", "grouping",
                    "chronological_order", "calculation", "turning_points"]
                   + ([] if limitations else ["request_alignment", "unit"])),
    )
