"""Per-series full trajectories and exact cross-series endpoint differences."""
from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.trend_calculations import decimal_value, exact_difference
from app.agent.query.trend_render import _period, _value, render_trend, trend_witness_indices


def comparison_sections(series, direct):
    sections, references = [], []
    for candidate, units in series:
        points = candidate.observations
        note = getattr(candidate, "period_note", "")
        sections.append(f"원본 범위: {candidate.table_id}\n" + (note + "\n" if note else "")
                        + render_trend(points, units))
        references.extend(candidate.context)
        witnesses = trend_witness_indices(points)
        if len(points) <= 100:
            witnesses |= set(range(len(points)))
        for number in sorted(witnesses):
            point, unit = points[number], units[number]
            references.extend((point.label, point.period_cell, point.value, *point.context_cells,
                               *point.entity_cells, *unit.references))
    if direct:
        sections.append(_differences(series))
    return "\n\n".join(sections), [_evidence(cell) for cell in dict.fromkeys(references)]


def _differences(series):
    first, first_units = series[0]
    points = first.observations
    spec = parse_number_format(points[0].value.number_format)
    unit = first_units[0]
    label = str(points[0].label.value)
    before, after = decimal_value(points[0].value.value), decimal_value(points[-1].value.value)
    change = exact_difference(before, after)
    lines = ["동일 관측 시점·단위의 항목 비교:"]
    for candidate, _ in series[1:]:
        other = candidate.observations
        name = str(other[0].label.value)
        other_before, other_after = decimal_value(other[0].value.value), decimal_value(other[-1].value.value)
        end_gap = exact_difference(other_after, after)
        delta_gap = exact_difference(exact_difference(other_before, other_after), change)
        lines.append(f"- 마지막 관측값 차이({label} - {name}), {_period(points[-1])}: "
                     f"{_signed(end_gap, spec, unit)}.")
        lines.append(f"- 전체 기간 증감의 차이({label} - {name}), "
                     f"{_period(points[0])} → {_period(points[-1])}: {_signed(delta_gap, spec, unit)}.")
    return "\n".join(lines)


def _signed(value, spec, unit):
    sign = "+" if value > 0 else "-" if value < 0 else ""
    rendered = _value(value.copy_abs(), spec, unit)
    return sign + (rendered.removesuffix("%") + "%p" if spec.percent else rendered)
