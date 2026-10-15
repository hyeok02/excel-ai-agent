"""Aggregate compatible source units with decimal arithmetic and Excel formats."""
import math
from dataclasses import replace
from decimal import Decimal, localcontext

from app.agent.query.excel_number_formats import display_value, parse_number_format


def numeric_summary(values, formats):
    entries = [(value, style) for value, style in zip(values, formats)
               if value not in (None, "")]
    if not entries or any(not isinstance(value, (int, float)) or isinstance(value, bool)
                          or not math.isfinite(value) for value, _ in entries):
        return None, []
    specs = [parse_number_format(style) for _, style in entries]
    # An unsupported date/fraction/clock format must not silently become a plain unit.
    if any(spec.mode == "raw" and style.casefold().strip() != "general"
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
        if value == value.to_integral_value():
            return f"{int(value):,}"
        whole, fraction = format(value, "f").split(".")
        sign = "-" if whole.startswith("-") else ""
        return f"{sign}{abs(int(whole)):,}.{fraction.rstrip('0')}"
    if not spec.mode:
        scaled = value * spec.multiplier / spec.divisor
        decimals = max(0, -scaled.normalize().as_tuple().exponent)
        # Computed means can need more decimals than the original integer cells.
        spec = replace(spec, maximum_decimals=max(spec.maximum_decimals, min(decimals, 12)))
    return display_value(value, spec)
