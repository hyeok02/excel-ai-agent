"""Constant-space decimal statistics with the existing source-unit rules."""
from dataclasses import replace
from decimal import Decimal, localcontext

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.tabular_filters import finite_number
from app.agent.query.tabular_numeric import _render, _unit_identity


class NumericAccumulator:
    def __init__(self):
        self.count = self.blanks = 0
        self.total = Decimal(0)
        self.minimum = self.maximum = self.spec = None
        self.styles = {}

    def add(self, value, style):
        if value in (None, ""):
            self.blanks += 1
            return True
        if not finite_number(value):
            return False
        if style not in self.styles:
            if len(self.styles) >= 256:
                return False
            self.styles[style] = parse_number_format(style)
        spec = self.styles[style]
        if spec.mode == "raw" and style.casefold().strip() != "general":
            return False
        if self.spec is not None and _unit_identity(self.spec) != _unit_identity(spec):
            return False
        if self.spec is None:
            self.spec = spec
        else:
            self.spec = replace(self.spec, minimum_decimals=max(self.spec.minimum_decimals, spec.minimum_decimals),
                                maximum_decimals=max(self.spec.maximum_decimals, spec.maximum_decimals),
                                mode="raw" if spec.mode == "raw" else self.spec.mode)
        number = Decimal(str(value))
        exponent = min(number.as_tuple().exponent, self.total.as_tuple().exponent)
        with localcontext() as context:
            context.prec = max(28, number.adjusted() - exponent + 3, self.total.adjusted() - exponent + 3)
            self.total += number
        self.minimum = number if self.minimum is None else min(self.minimum, number)
        self.maximum = number if self.maximum is None else max(self.maximum, number)
        self.count += 1
        return True

    def render(self, statistic):
        if not self.count:
            return None
        with localcontext() as context:
            context.prec = max(28, len(self.total.as_tuple().digits) + abs(self.total.as_tuple().exponent)
                               + len(str(self.count)) + 5)
            values = [self.total, self.total / self.count, self.minimum, self.maximum]
            rendered = [_render(value, self.spec) for value in values]
        if statistic == "all":
            return (f"숫자 {self.count}건, 합계 {rendered[0]}, 평균 {rendered[1]}, "
                    f"최솟값 {rendered[2]}, 최댓값 {rendered[3]}, 빈칸 {self.blanks}건")
        positions = {"sum": (0, "합계"), "average": (1, "평균"), "min": (2, "최솟값"), "max": (3, "최댓값")}
        position, label = positions[statistic]
        return f"{label} {rendered[position]} (숫자 {self.count}건, 빈칸 {self.blanks}건)"
