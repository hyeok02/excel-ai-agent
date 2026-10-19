"""Post-aggregation predicates and shares, independent of display/rank limits."""
from decimal import Decimal, localcontext

from app.agent.query.tabular_numeric import _render

COMPARISONS = {
    "equals": lambda left, right: left == right,
    "not_equals": lambda left, right: left != right,
    "greater_than": lambda left, right: left > right,
    "greater_than_or_equal": lambda left, right: left >= right,
    "less_than": lambda left, right: left < right,
    "less_than_or_equal": lambda left, right: left <= right,
}


def aggregate_value(plan, group, column=None):
    if plan.operation == "row_count":
        return Decimal(group.count)
    if plan.operation == "distinct_count":
        return Decimal(len(group.distinct))
    return group.numeric[column].value(plan.statistic)


class AggregatePostprocess:
    def __init__(self, state):
        self.state, self.plan = state, state.plan
        self.denominator = None
        self.shares = {}

    def select(self, groups):
        if self.plan.share_of_total and not self._shares(groups):
            return None
        selected = []
        for group in groups:
            outcomes = [self._matches(group, condition) for condition in self.plan.having]
            if any(outcome is None for outcome in outcomes):
                return None
            if all(outcomes):
                selected.append(group)
        return selected

    def _shares(self, groups):
        column = self.state.measures[0] if self.state.measures else None
        values = [aggregate_value(self.plan, group, column) for group in groups]
        if any(value is None or value < 0 for value in values):
            return False
        # Reuse the exact, full-population running sum. Summing group totals
        # under precision based on each value alone can lose a tiny group next
        # to a huge group, incorrectly certifying the huge group as exactly 100%.
        denominator = (self.state.units[column].total if column
                       else Decimal(sum(group.count for group in groups)))
        if denominator <= 0:
            return False
        self.denominator = denominator
        with localcontext() as context:
            context.prec = max(40, len(denominator.as_tuple().digits) + 10,
                               *(len(value.as_tuple().digits) + 10 for value in values))
            self.shares = {id(group): value * 100 / denominator for group, value in zip(groups, values)}
        return True

    def _matches(self, group, condition):
        if condition.target == "share":
            column = self.state.measures[0] if self.state.measures else None
            numerator = aggregate_value(self.plan, group, column)
            threshold = Decimal(str(condition.value))
            # Compare exact cross products: rounded display ratios never decide HAVING.
            with localcontext() as context:
                context.prec = max(40, len(numerator.as_tuple().digits) + 5,
                                   len(threshold.as_tuple().digits) + len(self.denominator.as_tuple().digits) + 5)
                return COMPARISONS[condition.operator](numerator * 100, threshold * self.denominator)
        else:
            value = aggregate_value(self.plan, group, condition.column_id)
            if value is None:
                return None
            if condition.value_unit == "percent":
                accumulator = group.numeric[condition.column_id]
                spec, header = accumulator.spec, self.state.columns[condition.column_id].header
                if not spec.percent and "%" not in header and "percent" not in header.casefold():
                    return None
                with localcontext() as context:
                    context.prec = max(40, len(value.as_tuple().digits) + 5)
                    value *= spec.multiplier
        return COMPARISONS[condition.operator](value, Decimal(str(condition.value)))

    def share_text(self, group):
        if not self.plan.share_of_total:
            return None
        column = self.state.measures[0] if self.state.measures else None
        numerator = aggregate_value(self.plan, group, column)
        render = (lambda value: _render(value, self.state.units[column].spec)) if column else str
        with localcontext() as context:
            context.prec = 12
            percentage = format(+self.shares[id(group)], "f").rstrip("0").rstrip(".")
            # Preserve integral percentages (including 100) when stripping decimal zeros.
            if self.shares[id(group)] == self.shares[id(group)].to_integral_value():
                percentage = str(int(self.shares[id(group)]))
        with localcontext() as context:
            context.prec = max(40, len(numerator.as_tuple().digits) + abs(numerator.as_tuple().exponent) + 10,
                               len(self.denominator.as_tuple().digits) + abs(self.denominator.as_tuple().exponent) + 10)
            fraction = f"분자 {render(numerator)} / 분모 {render(self.denominator)}"
        return f"전체 대비 비중 약 {percentage}% ({fraction})"
