"""Deterministic growth and explicit-operand share trends, before generation."""
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification
from app.agent.query.trend_comparison_scope import comparison_limits
from app.agent.query.trend_request import trend_request_error, asks_trend
from app.agent.query.derived_trend_request import GROWTH, SHARE, YOY, MOM, PREVIOUS, metric_tokens, derived_request, source_question
from app.agent.query.metric_observation_periods import requested_periods
from app.agent.query.derived_trend_sources import initial_sources, operand_sources
from app.agent.query.derived_trend_calculations import growth_points, share_points
from app.agent.query.derived_trend_render import render_derived


def derived_trend_answer(question, summary, index):
    if not (GROWTH.search(question) or SHARE.search(question)):
        return None
    if (GROWTH.search(question) and not asks_trend(question) and len(requested_periods(question)) == 2
            and not any(pattern.search(question) for pattern in (YOY, MOM, PREVIOUS))):
        # A two-period amount+rate question belongs to the endpoint comparison
        # executor, not a derived series that only renders period growth rates.
        return None
    initial, named = initial_sources(question, summary, index)
    masked, labels = metric_tokens(question, initial)
    request, error = derived_request(masked, labels)
    if error:
        return unavailable(question, error)
    if request is None:
        return None
    clean = source_question(masked, labels)
    initial, named = initial_sources(clean, summary, index)
    series, bounds, error = operand_sources(request, question, clean, initial, named, summary, index)
    if error:
        return unavailable(question, error)
    observations = tuple(point for candidate, _ in series for point in candidate.observations)
    if error := trend_request_error(clean, observations, named):
        return unavailable(question, error)
    limitations = []
    if request.kind == "share":
        if limits := comparison_limits(series):
            return unavailable(question, "분자·분모의 날짜·단위·대상 범위를 함께 확인하지 못했습니다. " + " ".join(limits))
    else:
        candidate, units = series[0]
        if not all(unit.known for unit in units):
            limitations.append("증감률은 동일 원본 저장값 기준이며 수량·통화 단위까지는 확정하지 못했습니다.")
        if candidate.hidden_rows:
            limitations.append(f"숨겨진 {candidate.hidden_rows}개 행을 제외한 표시 데이터의 증감률입니다.")
    try:
        if request.kind == "growth":
            points, skipped = growth_points(series[0][0], bounds, request.basis, request.decrease)
        else:
            points, skipped = share_points(series[0][0], series[1][0], component=request.component), ()
        text, evidence = render_derived(request, points, skipped, series, bounds.note)
    except (ValueError, TypeError, ArithmeticError) as exc:
        return unavailable(question, str(exc) or "파생 시계열의 전체 계산을 확인하지 못했습니다.")
    return QuestionAnswer(
        question=question, answer=text, status="limited" if limitations else "answered",
        confidence=0.85 if limitations else 1, selected_tools=["chronological_trend", "derived_trend"],
        evidence=evidence, limitations=limitations,
        verification=QuestionAnswerVerification(
            level="source_checked" if limitations else "request_checked",
            checks=["table_scope", "metric", "complete_series", "source_values", "chronological_order",
                    "calculation", "turning_points", "aligned_periods", "positive_denominator", "operand_lineage"]
                   + ([] if limitations else ["unit", "request_alignment", "aligned_entity_scope"]),
        ),
    )


def unavailable(question, reason):
    return QuestionAnswer(question=question, answer=reason, status="insufficient_evidence", confidence=0,
                          selected_tools=["chronological_trend", "derived_trend"], evidence=[], limitations=[reason])
