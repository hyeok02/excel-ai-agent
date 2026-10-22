"""Plain-language ranking with explicit path versus endpoint distinctions."""
from decimal import Decimal, localcontext

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.trend_calculations import decimal_value
from app.agent.query.trend_render import _number, _period, _value


def render_ranking(ranking, request, group_label, net=None):
    group = group_label.removesuffix("별") or "항목"
    direction = "감소" if request.direction == "decrease" else "증가"
    basis = {
        "net": "전체 기간 시작→끝",
        "extreme_to_latest": "고점→마지막" if request.direction == "decrease" else "저점→마지막",
        "max_drawdown": "기간 중 고점→이후 저점" if request.direction == "decrease" else "기간 중 저점→이후 고점",
        "adjacent": "인접한 두 관측 시점 사이",
    }[ranking.basis]
    suffix = "율" if request.percent else "량"
    lines = [f"{basis} 기준으로 {direction}{suffix}을 비교했습니다."]
    if ranking.winners:
        names = ", ".join(_name(item) for item in ranking.winners)
        tie = f"(공동 1위 {len(ranking.winners)}개)" if len(ranking.winners) > 1 else ""
        lines.append(f"{direction}{suffix}이 가장 큰 {group}: {names}{tie}.")
        lines.extend(_line(item, request) for item in ranking.winners)
    else:
        lines.append(f"이 기준으로 {direction}한 {group}가 없습니다.")
    if net is not None:
        lines.extend(["", "전체 기간 시작→끝 비교:"])
        if net.winners:
            names = ", ".join(_name(item) for item in net.winners)
            tie = f"(공동 1위 {len(net.winners)}개)" if len(net.winners) > 1 else ""
            lines.append(f"최초값과 마지막값만 비교하면 {direction}{suffix}이 가장 큰 {group}는 {names}{tie}입니다.")
            lines.extend(_line(item, request) for item in net.winners)
        else:
            lines.append(f"전체 기간 시작→끝 기준으로는 {direction}한 {group}가 없습니다.")
            changes = [item.difference for item in net.metrics]
            if all(change > 0 for change in changes):
                lines.append(f"비교한 {len(changes)}개 {group} 모두 증가했습니다.")
            elif all(change < 0 for change in changes):
                lines.append(f"비교한 {len(changes)}개 {group} 모두 감소했습니다.")
            elif all(change == 0 for change in changes):
                lines.append(f"비교한 {len(changes)}개 {group} 모두 시작값과 마지막값이 같습니다.")
        lines.append("기간 중 감소·증가와 전체 기간 순증감은 서로 다른 비교 기준입니다.")
    first = ranking.metrics[0].candidate.observations
    lines.extend(["", f"비교 기간: {_period(first[0])} → {_period(first[-1])}.",
                  f"비교 대상({len(ranking.metrics)}개): " + ", ".join(_name(item) for item in ranking.metrics) + ".",
                  "원본 범위: " + "; ".join(dict.fromkeys(item.candidate.table_id for item in ranking.metrics))])
    notes = dict.fromkeys(item.candidate.period_note for item in ranking.metrics if item.candidate.period_note)
    lines.extend(notes)
    return "\n".join(lines)


def _name(item):
    return str(item.candidate.observations[0].label.value)


def _line(item, request):
    points = item.candidate.observations
    before, after = points[item.start], points[item.end]
    unit = item.units[item.start]
    spec = parse_number_format(before.value.number_format)
    if spec.mode not in {"", "raw"}:
        raise ValueError("비교 수치의 표시 형식을 확정하지 못했습니다.")
    change = _value(item.difference.copy_abs(), spec, unit)
    if spec.percent:
        change = change.removesuffix("%") + "%p"
    direction = "감소" if item.difference < 0 else "증가" if item.difference > 0 else "변동 없음"
    rate = f"; {direction}율 {_rate(item.score)}%" if request.percent else ""
    return (f"- {_name(item)}: {_period(before)} → {_period(after)}, "
            f"{_value(decimal_value(before.value.value), spec, unit)} → "
            f"{_value(decimal_value(after.value.value), spec, unit)}, {change} {direction}{rate}.")


def _rate(number):
    """Round presentation only; a tiny real rate must never appear as zero."""
    with localcontext() as context:
        context.prec = max(32, len(number.as_tuple().digits), number.adjusted() + 8)
        rounded = number.quantize(Decimal("0.01"))
    if rounded == number:
        return _number(rounded)
    return "약 " + (_number(rounded) if rounded else format(number, ".2E"))
