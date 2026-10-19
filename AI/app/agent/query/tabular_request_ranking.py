"""Verify top/bottom-N selection, including ranks already stored in a source."""
import re
import math
from decimal import Decimal

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.tabular_validation import filtered_rows, ordered_rows
from app.agent.query.tabular_ranking_language import ranking_request

_FIRST = re.compile(r"(?:앞의|처음|첫|first)\s*(\d+)", re.I)


def ranking_constraints_match(text, plan, table, *, streaming=False):
    grouped = getattr(plan, "group_by", ())
    per = getattr(plan, "per_group_limit", None)
    request = ranking_request(text, table, grouped=bool(grouped), excluded=grouped)
    if request is False:
        return False, frozenset()
    if request is None:
        first = _FIRST.search(text)
        if first:
            return not plan.order_by and not grouped and plan.limit == int(first.group(1)), frozenset()
        return plan.limit is None and plan.order_by is None and per is None, frozenset()
    count, descending, requested_metric = request.count, request.descending, request.metric
    if grouped:
        if per is not None:
            return (plan.operation == "row_list" and plan.limit is None and per == count
                    and requested_metric == plan.order_by and plan.order_by is not None
                    and plan.descending == descending), frozenset()
        metric_ok = (plan.order_by is None and plan.operation in {"row_count", "distinct_count"}
                     and (requested_metric is None or requested_metric in plan.column_ids)) or (
            plan.operation == "numeric_summary" and plan.statistic != "all"
            and len(plan.column_ids) == 1 and plan.order_by in plan.column_ids
            and requested_metric == plan.order_by)
        return (metric_ok and plan.limit == count and plan.descending == descending), frozenset()
    if streaming:
        # Witnesses are not the population. Complete-stream numeric/unit checks
        # belong to the accumulator; a sampled 1..N rank is never proof.
        return (plan.order_by is not None and requested_metric == plan.order_by
                and plan.limit == count and plan.descending == descending), frozenset()
    if plan.order_by and requested_metric in (None, plan.order_by):
        rows = filtered_rows(table, plan.filters)
        correct = (rows is not None and all(_number(row.values.get(plan.order_by)) for row in rows)
                   and _compatible_units(table, plan.order_by, rows) and plan.descending == descending
                   and plan.limit == count)
        return correct, frozenset()
    numeric = [column for column in dict.fromkeys([*plan.column_ids, plan.order_by]) if column is not None
               if all(_number(row.values.get(column)) for row in table.rows)]
    if count is None:
        return False, frozenset()
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


def _compatible_units(table, column, rows=None):
    specs = [parse_number_format(row.number_formats.get(column, "General"))
             for row in (table.rows if rows is None else rows)]
    return len({(spec.percent, spec.multiplier, spec.divisor, spec.prefix, spec.suffix, spec.mode)
                for spec in specs}) <= 1
