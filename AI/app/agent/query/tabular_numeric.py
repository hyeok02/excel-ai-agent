"""Aggregate compatible source units with decimal arithmetic and Excel formats."""
import math
import re
from dataclasses import replace
from decimal import ROUND_HALF_UP, Decimal, localcontext

from app.agent.query.excel_number_formats import display_value, parse_number_format


def numeric_summary(values, formats, statistic="all"):
    entries = [(value, style) for value, style in zip(values, formats)
               if value not in (None, "")]
    if not entries or any(not isinstance(value, (int, float)) or isinstance(value, bool)
                          or not math.isfinite(value) for value, _ in entries):
        return None, []
    specs = [parse_number_format(style) for _, style in entries]
    # An unsupported date/fraction/clock format must not silently become a plain unit.
    if any(spec.mode == "raw" and re.sub(r'"[^"]*"', "", style).casefold().strip() != "general"
           for (_, style), spec in zip(entries, specs)):
        return None, []
    if len({_unit_identity(spec) for spec in specs}) != 1:
        return None, []
    spec = replace(
        specs[0], minimum_decimals=max(item.minimum_decimals for item in specs),
        maximum_decimals=max(item.maximum_decimals for item in specs),
        mode="raw" if any(item.mode == "raw" for item in specs) else specs[0].mode,
    )
    numbers = [Decimal(str(value)) for value, _ in entries]
    precision = max(28, *(len(number.as_tuple().digits) + abs(number.as_tuple().exponent)
                          + len(str(len(numbers))) + 5 for number in numbers))
    with localcontext() as context:
        context.prec = precision
        total = sum(numbers, Decimal(0))
        average = total / len(numbers)
        rendered = [_render(value, spec) for value in (total, average, min(numbers), max(numbers))]
    if statistic != "all":
        positions = {"sum": (0, "합계"), "average": (1, "평균"),
                     "min": (2, "최솟값"), "max": (3, "최댓값")}
        if statistic not in positions:
            return None, []
        position, label = positions[statistic]
        return f"{label} {rendered[position]} (숫자 {len(numbers)}건, 빈칸 {len(values) - len(numbers)}건)", []
    text = (
        f"숫자 {len(numbers)}건, 합계 {rendered[0]}, 평균 {rendered[1]}, "
        f"최솟값 {rendered[2]}, 최댓값 {rendered[3]}, 빈칸 {len(values) - len(numbers)}건"
    )
    return text, []


def _unit_identity(spec):
    return (spec.prefix, spec.suffix, spec.percent, spec.multiplier, spec.divisor,
            "" if spec.mode == "raw" else spec.mode)


def _render(value, spec):
    if spec.mode == "raw":
        # Binary float noise and long means are cut to a readable precision.
        with localcontext() as context:
            context.prec = max(28, value.adjusted() + _places(value) + 3)
            value = value.quantize(Decimal(1).scaleb(-_places(value)), rounding=ROUND_HALF_UP)
        if value == value.to_integral_value():
            text = f"{abs(int(value)):,}"
        else:
            whole, fraction = format(abs(value), "f").split(".")
            text = f"{int(whole):,}.{fraction.rstrip('0')}"
        # A unit inherited around General ("$"General) stays beside the number.
        return f"{'-' if value < 0 else ''}{spec.prefix}{text}{spec.suffix}"
    if not spec.mode:
        scaled = value * spec.multiplier / spec.divisor
        decimals = max(0, -scaled.normalize().as_tuple().exponent)
        # Computed means can need more decimals than the original integer cells.
        spec = replace(spec, maximum_decimals=max(spec.maximum_decimals, min(decimals, _places(scaled))))
    return display_value(value, spec)


def _places(value):
    """Two decimals from 1 up; three significant digits below 1 (0.00123), at most 12."""
    if not value or abs(value) >= 1:
        return 2
    return min(12, 2 - abs(value).adjusted())
