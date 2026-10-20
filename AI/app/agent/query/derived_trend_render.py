"""Show derived trajectories and cite only their unchanged source operands."""
from dataclasses import replace
from decimal import Decimal, localcontext

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.trend_calculations import calculate_trend, exact_difference
from app.agent.query.trend_render import _period


def render_derived(request, points, skipped, series, note):
    labels = request.labels
    name = labels[0] + (" 감소율" if request.decrease else " 증감률") if request.kind == "growth" else f"{labels[0]} / {labels[1]} 비율"
    basis = {"year": "전년 같은 시점", "month": "전월 같은 시점", "previous": "이전 관측값"}[request.basis]
    formula = ("(이전 기준값 - 현재값) / 이전 기준값 × 100" if request.decrease else
               "(현재값 - 이전 기준값) / 이전 기준값 × 100") if request.kind == "growth" else "분자 / 분모 × 100"
    lines = ["원본 범위: " + ", ".join(dict.fromkeys(candidate.table_id for candidate, _ in series)),
             f"{name}: {len(points)}개 시점. 계산식: {formula}."]
    if note:
        lines.append(note)
    if request.kind == "growth":
        lines.append(f"증감률 비교 기준: {basis}. 원본 금액·인원의 증감과 증감률 자체의 상승·하락은 구분합니다.")
    if skipped:
        lines.append(f"최초 {len(skipped)}개 관측은 앞선 비교 기준값이 없어 증감률 계산 대상에서 제외했습니다. "
                     f"계산 가능한 기간은 {_period(points[0].current)}부터입니다.")
    virtual = tuple(replace(point.current, value=replace(point.current.value, value=point.value)) for point in points)
    trend = calculate_trend(virtual)
    lines.append(f"전체 시작·끝: {_percent(points[0].value)} → {_percent(points[-1].value)}, "
                 f"{_movement(points[0].value, points[-1].value)}.")
    lines.append(f"날짜순 인접 구간: 상승 {trend.rising}회, 하락 {trend.falling}회, 보합 {trend.flat}회.")
    if trend.rising and trend.falling:
        lines.append("중간에 상승과 하락이 모두 있어, 시작·끝 변화가 지속적인 한 방향 변화를 뜻하지는 않습니다.")
    lines.append("시점별 계산값:")
    shown = points if len(points) <= 100 else (*points[:50], *points[-50:])
    for number, point in enumerate(shown):
        if len(points) > 100 and number == 50:
            lines.append(f"- 중간 {len(points) - 100}개 시점의 상세 표시만 생략했습니다. 전체 시점은 계산·검증에 포함했습니다.")
        base = f" (비교 기준일 {_period(point.base)})" if request.kind == "growth" else ""
        lines.append(f"- {_period(point.current)}: {_percent(point.value)}{base}.")
    runs = trend.runs if len(trend.runs) <= 12 else (*trend.runs[:6], *trend.runs[-6:])
    for run in runs:
        direction = {1: "상승", -1: "하락", 0: "보합"}[run.direction]
        if run.reversal:
            direction += "(하락 뒤 반등)" if run.direction > 0 else "(상승 뒤 하락 전환)"
        lines.append(f"- {_period(points[run.start].current)} → {_period(points[run.end].current)}: {direction}.")
    for title, indices in (("최고", trend.maximum), ("최저", trend.minimum)):
        dates = ", ".join(_period(points[number].current) for number in indices[:6])
        lines.append(f"{title}: {_percent(points[indices[0]].value)}, {dates}" + (f" 외 {len(indices) - 6}개 시점." if len(indices) > 6 else "."))
    return "\n".join(lines), _lineage(points, series, skipped)


def _percent(value):
    with localcontext() as context:
        context.prec = max(40, len(value.as_tuple().digits) + 8, value.adjusted() + 8)
        raw = value * 100
        rounded = raw.quantize(Decimal("0.01"))
    return (format(rounded, ",f").rstrip("0").rstrip(".") if rounded else (format(raw, ".2E") if raw else "0")) + "%"


def _movement(before, after):
    delta = exact_difference(before, after)
    return "변동 없음" if not delta else _percent(delta.copy_abs()).removesuffix("%") + "%p " + ("증가" if delta > 0 else "감소")


def _lineage(points, series, skipped):
    references = [cell for candidate, _ in series for cell in candidate.context]
    for point in points:
        for source in (point.current, point.base):
            references.extend((source.label, source.value, source.period_cell, *source.context_cells, *source.entity_cells))
    for source in skipped:
        references.extend((source.label, source.value, source.period_cell, *source.context_cells, *source.entity_cells))
    references.extend(cell for _, units in series for unit in units for cell in unit.references)
    return [_evidence(cell) for cell in dict.fromkeys(references)]
