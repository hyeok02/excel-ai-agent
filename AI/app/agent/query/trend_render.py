"""Bounded Korean trend explanation; never confuse net growth with a path."""
import re
from decimal import Decimal, localcontext

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.trend_calculations import (
    calculate_trend, change_percent, display_scale, exact_difference,
)

MAX_DISPLAY_RUNS = 12
MAX_EXTREME_PERIODS = 6


def trend_witness_indices(observations):
    """Sorted-series cell witnesses for every explicitly displayed date/value."""
    trend = calculate_trend(observations)
    indices = {0, len(trend.values) - 1, len(trend.values) - 2}
    indices.update(trend.minimum[:MAX_EXTREME_PERIODS])
    indices.update(trend.maximum[:MAX_EXTREME_PERIODS])
    for run in _shown_runs(trend):
        indices.update((run.start, run.end))
    return indices


def _shown_runs(trend):
    runs = trend.runs
    return runs if len(runs) <= MAX_DISPLAY_RUNS else (*runs[:6], *runs[-6:])


def render_trend(observations, units) -> str:
    if len(observations) != len(units) or len({unit.identity for unit in units}) != 1:
        raise ValueError("추이의 전체 관측값에 같은 단위가 필요합니다.")
    trend = calculate_trend(observations)
    unit = units[0]
    spec = parse_number_format(trend.observations[0].value.number_format)
    if spec.mode not in {"", "raw"}:
        raise ValueError("시간 길이 표시 형식은 추이 수치로 표시하지 않습니다.")
    dates = [_period(item) for item in trend.observations]
    value = lambda index: _value(trend.values[index], spec, unit)
    movement = lambda start, end: _movement(trend.values[start], trend.values[end], spec, unit)
    lines = [f"{trend.observations[0].label.value}: {dates[0]} → {dates[-1]}, "
             f"날짜순으로 {len(dates)}개 관측값을 확인했습니다.",
             f"전체 시작·끝 비교: {value(0)} → {value(-1)}, {movement(0, -1)}.",
             f"인접 관측 구간: 상승 {trend.rising}회, 하락 {trend.falling}회, 보합 {trend.flat}회."]
    if trend.rising and trend.falling:
        lines.append("중간에 상승과 하락이 모두 있어, 전체 순증감이 지속적인 상승·하락을 뜻하지는 않습니다.")
    lines.append("기간별 흐름:")
    runs = trend.runs
    shown = _shown_runs(trend)
    for index, run in enumerate(shown):
        if len(runs) > MAX_DISPLAY_RUNS and index == 6:
            lines.append(f"- 중간 {len(runs) - MAX_DISPLAY_RUNS}개 구간의 상세 표시는 생략했습니다. "
                         "전체 관측값은 계산에 포함했습니다.")
        direction = {1: "상승", -1: "하락", 0: "보합"}[run.direction]
        if run.reversal:
            direction += "(하락 뒤 반등)" if run.direction > 0 else "(상승 뒤 하락 전환)"
        lines.append(f"- {dates[run.start]} → {dates[run.end]}: "
                     f"{value(run.start)} → {value(run.end)}, {direction}; "
                     f"{movement(run.start, run.end)}.")
    for title, indices in (("최고", trend.maximum), ("최저", trend.minimum)):
        labels = ", ".join(dates[index] for index in indices[:MAX_EXTREME_PERIODS])
        if len(indices) > MAX_EXTREME_PERIODS:
            labels += f" 외 {len(indices) - MAX_EXTREME_PERIODS}개 시점(날짜 표시 생략)"
        lines.append(f"{title}값: {value(indices[0])}, {labels}"
                     + (f"(동률 {len(indices)}개 시점)." if len(indices) > 1 else "."))
    lines.append(f"최근 관측 구간: {dates[-2]} → {dates[-1]}, "
                 f"{value(-2)} → {value(-1)}, {movement(-2, -1)}.")
    if not spec.percent and any(number <= 0 for number in trend.values[:-1]):
        lines.append("시작값이 0 이하인 구간은 증감률을 계산하지 않았습니다.")
    return "\n".join(lines)


def _number(number):
    # Source direction is never inferred from rounded display strings. Retain
    # even sub-cent/tiny movements; use scientific notation for long values.
    if not number:
        return "0"
    rendered = format(number, ",f")
    if "." in rendered:
        rendered = rendered.rstrip("0").rstrip(".")
    if len(rendered) <= 32:
        return rendered
    with localcontext() as context:
        context.prec = max(32, len(number.as_tuple().digits))
        return format(number.normalize(), "E")


def _value(number, spec, unit):
    scaled = display_scale(number, spec.multiplier, spec.divisor)
    suffix = spec.suffix or ("%" if spec.percent else unit.suffix)
    return f"{spec.prefix}{_number(scaled)}{suffix}"


def _movement(before, after, spec, unit):
    difference = exact_difference(before, after)
    if not difference:
        return "변동 없음"
    verb = "증가" if difference > 0 else "감소"
    if spec.percent or unit.suffix == "%":
        moved = display_scale(difference.copy_abs(), spec.multiplier, spec.divisor)
        return f"{_number(moved)}%p {verb}"
    text = f"{_value(difference.copy_abs(), spec, unit)} {verb}"
    rate = change_percent(before, after)
    if rate is None:
        return text
    with localcontext() as context:
        context.prec = max(32, len(rate.as_tuple().digits), rate.adjusted() + 8)
        rounded = rate.quantize(Decimal("0.01"))
    percentage = _number(rounded) if rounded else format(rate, ".2E")
    return f"{text}({'+' if rate > 0 else ''}{percentage}%)"


def _period(observation):
    date, source = observation.period, str(observation.period_cell.value).strip()
    if re.fullmatch(r"(?:FY\s*)?\d{4}(?:\s*[AE])?", source, re.I):
        text = f"{date.year}년"
    elif re.fullmatch(r"\d{4}[-/.]\d{1,2}", source):
        text = f"{date.year}년 {date.month}월"
    else:
        text = date.isoformat(sep=" ") if any((date.hour, date.minute, date.second, date.microsecond)) else date.date().isoformat()
    grain = {"annual": "연간", "quarter": "분기", "month": "월간", "ltm": "최근 12개월"}.get(observation.grain)
    scenario = {"actual": "실적", "estimate": "예상", "budget": "예산"}.get(observation.scenario)
    suffix = " ".join(part for part in (grain, scenario) if part)
    return text + (f"({suffix})" if suffix else "")
