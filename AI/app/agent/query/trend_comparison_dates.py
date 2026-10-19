"""Recheck final comparison windows using only its selected source identities."""
from dataclasses import replace

from app.agent.query.trend_date_bounds import parse_trend_date_bounds, select_trend_periods
from app.agent.query.trend_labels import trend_label_spellings


def checked_comparison_periods(question, series, named):
    """Reject upstream calendar masking mistakes before certifying any values.

    Each relative window keeps that series' own latest source observation.
    Other selected metric labels are names, not unrelated calendar mentions.
    Previously narrowed windows cannot be expanded from retained points alone.
    """
    source_names = {*named, *(label for candidate, _ in series for label in
                             trend_label_spellings(candidate.observations[0].label.value))}
    checked = []
    for candidate, units in series:
        points = candidate.observations
        bounds, error = parse_trend_date_bounds(question, points, source_names)
        if error:
            return [], error
        selected = select_trend_periods(points, bounds)
        if len(selected) != len(points) or len(selected) < 2:
            return [], "비교에 포함된 원본 시점이 최종 질문의 날짜 범위와 일치하지 않아 결과를 표시하지 않았습니다."
        previous = getattr(candidate, "period_note", "")
        if previous and previous != bounds.note:
            return [], "원본을 선택한 기간과 최종 비교 요청의 기간이 달라 전체 범위를 확인하지 못했습니다."
        checked.append((replace(candidate, period_note=bounds.note), units))
    return checked, None
