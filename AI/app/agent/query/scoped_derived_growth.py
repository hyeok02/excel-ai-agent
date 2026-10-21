"""Apply each rate baseline to the same fully bound source population."""
from app.agent.query.derived_trend_calculations import growth_points
from app.agent.query.derived_trend_render import render_derived
from app.agent.query.derived_trend_request import DerivedRequest, derived_request
from app.agent.query.scoped_derived_request import source_operation
from app.agent.query.grouped_trend_series import grouped_series
from app.agent.query.scoped_derived_sources import expanded_growth_source
from app.agent.query.scoped_derived_render import validate_request, composite_answer


def scoped_growth(question, source, named, index, summary=None):
    masked = source_operation(question, source)
    request, error = derived_request(masked + " 추이", (source.metric.header,))
    if error or request is None or request.kind != "growth":
        raise ValueError(error or "증감률 계산 기준을 확인하지 못했습니다.")
    expanded, bounds = expanded_growth_source(source, request.basis, named, index, summary)
    series = grouped_series(expanded, index)
    validate_request(source, series, named)
    parts = []
    for title, candidate, units, _ in series:
        points, skipped = growth_points(candidate, bounds, request.basis, request.decrease)
        label = f"{title} {source.metric.header}" if title else source.metric.header
        item = DerivedRequest("growth", (label,), request.basis, request.decrease)
        text, _ = render_derived(item, points, skipped, ((candidate, units),), bounds.note)
        parts.append(text)
    return composite_answer(question, source, parts, series, ["same_population_baseline", "turning_points"])
