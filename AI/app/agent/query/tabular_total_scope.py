"""Bind an overall quantity request to one arithmetically checked source total.

The model cannot invent a total-row filter merely by saying it means "all".
The source must contain one complete, unambiguous population and a stored total
that reconciles to every detail row for the requested measure.
"""
import math
import re
from decimal import Decimal

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.source_measure_labels import bound_header_mentions
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan

_TOTAL = re.compile(r"계|합계|총계|총합계|총합|전체|total|grand\s+total|overall|all", re.I)
_WHOLE = re.compile(r"(?<![\w])(?:전국|전체|모두|overall|all)(?![A-Za-z0-9_])", re.I)
_GEOGRAPHY = re.compile(r"시\s*도|시\s*군\s*구|지역|국가|나라|country|region|state|province|area", re.I)
_REQUEST = re.compile(r"[\s?!.]*(?:(?:의|이|가|은|는|총|모두|전체|수|개|명|건|곳|"
                      r"몇|얼마|얼마나|합계|총합|총계|인가요|이야|야|인가|인지|입니까|"
                      r"알려줘|알려주세요|보여줘|보여주세요|the|is|are|what|how|many|"
                      r"much|total|sum|of|please|show|tell|me)[\s?!.]*)*", re.I)


def total_lookup_plan(question, table):
    binding = _request_binding(question, table)
    if binding is None:
        return None
    metric, identity, value = binding
    return TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=[metric],
                            filters=[TabularFilter(column_id=identity, operator="equals", value=value)])


def whole_total_filter_supported(question, plan, table, condition):
    if (not isinstance(plan, TabularQueryPlan)
            or plan.operation not in {"lookup", "numeric_summary"}
            or plan.operation == "numeric_summary" and plan.statistic != "sum"
            or len(plan.filters) != 1 or plan.group_by or plan.order_by or plan.limit
            or plan.filter_expression is not None or condition.operator != "equals"):
        return False
    binding = _request_binding(question, table)
    return bool(binding and plan.column_ids == [binding[0]]
                and condition.column_id == binding[1] and condition.value == binding[2])


def _request_binding(question, table):
    if not table.complete or table.excluded_rows or not _WHOLE.search(question):
        return None
    mentions = bound_header_mentions(question, table)
    metrics = {column for column, _ in mentions}
    if len(metrics) != 1:
        return None
    metric = next(iter(metrics))
    remainder = question
    for _, match in sorted(mentions, key=lambda item: item[1].start(), reverse=True):
        remainder = remainder[:match.start()] + " " * (match.end() - match.start()) + remainder[match.end():]
    remainder = _WHOLE.sub(" ", remainder)
    if not _REQUEST.fullmatch(remainder):
        return None  # No unaccounted period, location, exclusion, arithmetic or second metric.
    candidates = []
    for identity in table.columns:
        if identity.id == metric or identity.id in table.hidden_columns:
            continue
        if "전국" in question and not _GEOGRAPHY.fullmatch(identity.header.strip()):
            continue
        values = [row.values.get(identity.id) for row in table.rows]
        if not all(isinstance(value, str) and value.strip() for value in values):
            continue
        if len(set(values)) != len(values):
            continue
        totals = [row for row in table.rows if _TOTAL.fullmatch(str(row.values[identity.id]).strip())]
        if len(totals) != 1:
            continue
        total = totals[0]
        details = [row for row in table.rows if row is not total]
        if not details or not _reconciles(metric, total, details):
            continue
        candidates.append((metric, identity.id, total.values[identity.id]))
    return candidates[0] if len(candidates) == 1 else None


def _reconciles(metric, total, details):
    rows = [total, *details]
    values = [row.values.get(metric) for row in rows]
    if not all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
               for value in values):
        return False
    specs = [parse_number_format(row.number_formats.get(metric, "General")) for row in rows]
    if any(spec.percent for spec in specs) or len({(spec.multiplier, spec.divisor, spec.prefix,
                                                  spec.suffix, spec.mode) for spec in specs}) != 1:
        return False
    return Decimal(str(values[0])) == sum((Decimal(str(value)) for value in values[1:]), Decimal(0))
