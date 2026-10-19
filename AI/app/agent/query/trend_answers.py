"""Answer full chronological trajectories before any model-selected aggregate."""
from app.agent.query.ambiguity_candidates import AmbiguousCandidate, clarification_answer
from app.agent.query.ambiguity_metric_scope import bind_explicit_metric_scope
from app.agent.query.clarification_options import source_clarification_options
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.metric_observation_units import observation_unit
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from app.agent.query.trend_request import asks_trend, trend_request_error, bound_trend_periods
from app.agent.query.trend_selection import (
    scoped_trend_candidates, prepare_trend_candidate, distinct_trend_candidates,
)
from app.agent.query.trend_sources import trend_candidates
from app.agent.query.trend_render import render_trend, trend_witness_indices

_REASONS = {
    "ambiguous_date_axis": "한 지표에 연결할 날짜 열이 여러 개여서 임의로 선택하지 않았습니다.",
    "ambiguous_entity_scope": "서로 다른 회사·부서·지역 또는 시나리오가 섞여 있어 하나의 추이로 연결하지 않았습니다.",
    "missing_entity": "대상을 구분할 값이 비어 있어 같은 대상의 추이인지 확인하지 못했습니다.",
    "missing_or_invalid_value": "기간 중 숫자·수식 결과가 없거나 유효하지 않은 값이 있습니다. 이를 건너뛰거나 0으로 바꾸지 않았습니다.",
    "missing_or_invalid_date": "날짜가 없거나 읽을 수 없는 관측값이 있어 시간순 흐름을 확정하지 못했습니다.",
    "duplicate_period": "같은 날짜에 서로 다른 값이 있어 한 값으로 임의 선택하지 않았습니다.",
    "mixed_series_context": "기간의 길이·실적/예상 구분·단위가 달라 하나의 추이로 연결하지 않았습니다.",
    "conflicting_units": "원본 표시 형식과 단위 설명이 충돌하여 추이를 확정하지 못했습니다.",
    "insufficient_periods": "추이를 설명하려면 서로 다른 날짜의 유효한 값이 두 개 이상 필요합니다.",
    "resource_limit": "전체 시계열 확인 한도를 넘었습니다. 일부 기간만 읽고 전체 추이라고 답하지 않았습니다.",
}


def trend_answer(question, summary, index, intent=None):
    if not asks_trend(question):
        return None
    candidates, named = scoped_trend_candidates(question, trend_candidates(summary, index, question), summary)
    rows = list(index.rows)
    prepared = [prepare_trend_candidate(item, rows) for item in candidates]
    valid = distinct_trend_candidates([(item, units) for item, units in prepared if not item.error])
    if not valid:
        reason = next((_REASONS[item.error] for item, _ in prepared if item.error in _REASONS), None)
        return _unavailable(question, reason or "요청한 항목의 날짜와 전체 원본 값을 연결하지 못했습니다. 날짜 열과 지표가 있는 표를 지정해 주세요.")
    if any(item.error and item.error != "ambiguous_date_axis" for item, _ in prepared):
        return _unavailable(question, "같은 항목의 다른 원본 후보에 누락값이나 확인하지 못한 범위가 있습니다. 완전한 표만 임의로 선택하지 않았습니다. 사용할 시트와 표 범위를 지정해 주세요.")
    if len(valid) > 1:
        return clarification_answer(question, [_choice(question, item) for item, _ in valid], summary, index)
    candidate, units = valid[0]
    scope_ambiguous = any(item.error == "ambiguous_date_axis" for item, _ in prepared)
    _, scoped_question = bind_explicit_metric_scope(question, candidate.observations)
    if scoped_question != question:
        import re
        scoped_question = re.sub(r"범위(?:에서|의|내)?|\brange\b", " ", scoped_question, flags=re.I)
    if error := trend_request_error(scoped_question, candidate.observations, named):
        return _unavailable(question, error)
    points, error = bound_trend_periods(scoped_question, candidate.observations, named)
    if error:
        return _unavailable(question, error)
    units = tuple(observation_unit(point, rows) for point in points)
    try:
        text = render_trend(points, units)
        witnesses = trend_witness_indices(points) | (set(range(len(points))) if len(points) <= 100 else set())
    except (ValueError, TypeError, ArithmeticError):
        return _unavailable(question, "시계열의 날짜·단위·계산 결과를 확정하지 못했습니다.")
    references = [*candidate.context]
    for number in sorted(witnesses):
        point, unit = points[number], units[number]
        references.extend((point.label, point.period_cell, point.value, *point.context_cells,
                           *point.entity_cells, *unit.references))
    limitations = []
    if scope_ambiguous:
        limitations.append("다른 원본 후보에는 날짜 축이 여러 개 있습니다. 아래 명시한 표에서 확인한 추이만 표시하며, 질문의 대상 표까지 확정한 것은 아닙니다.")
    if not all(unit.known for unit in units):
        limitations.append("수치는 원본 저장값 기준입니다. 통화·수량 단위까지는 확정하지 못했습니다.")
    if candidate.hidden_rows:
        limitations.append(f"숨겨진 {candidate.hidden_rows}개 행을 제외한 표시 데이터의 추이입니다.")
    text = f"원본 범위: {candidate.table_id}\n" + text
    return QuestionAnswer(
        question=question, answer=text, status="limited" if limitations else "answered",
        confidence=0.9 if limitations else 1, selected_tools=["chronological_trend"],
        evidence=[_evidence(cell) for cell in dict.fromkeys(references)], limitations=limitations,
        clarification_options=source_clarification_options(question, [_choice(question, candidate)], summary, index)
        if scope_ambiguous else [],
        verification=QuestionAnswerVerification(
            level="source_checked" if limitations else "request_checked",
            checks=["table_scope", "metric", "complete_series", "source_values",
                    "chronological_order", "calculation", "turning_points"]
                   + (["alternative_source_ambiguous"] if scope_ambiguous else ["request_alignment"])
                   + (["unit"] if all(unit.known for unit in units) else []),
        ),
    )


def _unavailable(question, reason):
    return QuestionAnswer(question=question, answer=reason, status="insufficient_evidence", confidence=0,
                          selected_tools=["chronological_trend"], evidence=[], limitations=[reason])


def _choice(question, candidate):
    point = candidate.observations[0]
    sheet = point.value.sheet_name.replace("'", "''")
    reference = candidate.table_id.rpartition("!")[2]
    return AmbiguousCandidate(
        label=str(point.label.value), scope=candidate.table_id,
        details=f"{len(candidate.observations)}개 시점의 원본 값",
        followup=f"'{sheet}'!{reference} 범위에서 {question}",
        cells=tuple(dict.fromkeys((point.label, point.period_cell, point.value, *candidate.context))),
    )
