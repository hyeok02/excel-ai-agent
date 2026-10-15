"""Verify top/bottom-N selection, including ranks already stored in a source."""
import re
import math
from decimal import Decimal

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.tabular_validation import filtered_rows, ordered_rows

_RANKING = re.compile(r"(?P<direction>상위|하위|top|bottom)\s*(?P<count>\d+)", re.I)
_FIRST = re.compile(r"(?:앞의|처음|첫|first)\s*(\d+)", re.I)


def ranking_constraints_match(text, plan, table):
    matches = list(_RANKING.finditer(text))
    if not matches:
        first = _FIRST.search(text)
        if first:
            return plan.limit == int(first.group(1)), frozenset()
        return plan.limit is None, frozenset()
    if len(matches) != 1:
        return False, frozenset()
    match = matches[0]
    count = int(match.group("count"))
    descending = match.group("direction").casefold() in {"상위", "top"}
    numeric = [column for column in plan.column_ids
               if all(_number(row.values.get(column)) for row in table.rows)]
    preceding = [(found.end(), column.id) for column in table.columns
                 for found in re.finditer(re.escape(column.header), text, re.I)
                 if found.end() <= match.start() and match.start() - found.end() < 50]
    requested_metric = max(preceding, default=(0, None))[1]
    if plan.order_by:
        metric = plan.order_by
        if (requested_metric is None or requested_metric == metric) and metric in numeric:
            correct = (_compatible_units(table, metric) and plan.descending == descending
                       and plan.limit == count)
            return correct, frozenset()
    return _source_rank_matches(plan, table, numeric, requested_metric, count, descending)


def _source_rank_matches(plan, table, numeric, requested_metric, count, descending):
    # A source rank is acceptable only if it is a complete 1..N permutation,
    # its selected rows equal the requested N largest/smallest values, and the
    # answer's selected numeric metric proves that ordering independently. The
    # plan may either filter the rank or sort by it with an explicit row limit.
    metrics = [requested_metric] if requested_metric in numeric else [
        column for column in numeric if column != plan.order_by]
    if len(metrics) != 1 or (plan.limit is not None and plan.limit != count):
        return False, frozenset()
    metric = metrics[0]
    if not _compatible_units(table, metric):
        return False, frozenset()
    rank_columns = set()
    for column in table.columns:
        values = [row.values.get(column.id) for row in table.rows]
        if (all(_number(value) for value in values)
                and set(values) == set(range(1, len(values) + 1))
                and column.id != metric):
            rank_columns.add(column.id)
    rank_filters = {position for position, condition in enumerate(plan.filters)
                    if condition.column_id in rank_columns}
    if plan.order_by:
        if plan.order_by not in rank_columns or (plan.limit != count and not rank_filters):
            return False, frozenset()
    elif not rank_filters:
        return False, frozenset()
    base = filtered_rows(table, [item for position, item in enumerate(plan.filters)
                                 if position not in rank_filters])
    selected = filtered_rows(table, plan.filters)
    if base is None or selected is None:
        return False, frozenset()
    selected = ordered_rows(selected, plan)
    expected = sorted(base, key=lambda row: Decimal(str(row.values[metric])), reverse=descending)[:count]
    correct = (selected is not None and len(selected) == len(expected)
               and sorted(Decimal(str(row.values[metric])) for row in selected)
               == sorted(Decimal(str(row.values[metric])) for row in expected))
    return correct, frozenset(rank_filters)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _compatible_units(table, column):
    specs = [parse_number_format(row.number_formats.get(column, "General")) for row in table.rows]
    return len({(spec.percent, spec.multiplier, spec.divisor, spec.prefix, spec.suffix, spec.mode)
                for spec in specs}) <= 1
