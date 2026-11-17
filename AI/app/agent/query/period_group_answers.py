"""A total "by month/quarter/year" over a date column is computed per calendar period.

"월별 판매금액 알려줘" is planned as TotalPrice grouped by the Date column, which holds one date per
sale, so each day became its own group. When the question asks for a calendar grain and the
grouped column holds only dates, the rows are bucketed by that grain and listed in time order,
from every source row the plan's filters keep. Anything else about the plan is left as it was.
"""
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import re

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.ranked_group_units import shown_total, total_unit
from app.agent.query.resampled_trend_request import requested_grains
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_filters import filtered_rows
from app.agent.query.tabular_validation import validated_table

_LABELS = {"month": "월", "quarter": "분기", "annual": "연도"}
_SUBJECT = {"month": "달은", "quarter": "분기는", "annual": "해는"}
# "가장 많은 달은?" names the grain as the noun asked for, without "월별".
_NOUNS = {"month": r"(?<![가-힣])(?:달|몇\s*월)(?:은|는|이|가|에)?(?=\s|[?？.]|$)",
          "quarter": r"(?<![가-힣])분기(?:는|은|가|이|에)?(?=\s|[?？.]|$)",
          "annual": r"(?<![가-힣])(?:해|연도|년도)(?:는|은|가|이|에)?(?=\s|[?？.]|$)"}
_TOP = re.compile(r"가장|제일|최고|최대|\b(?:most|largest|highest|top|best)\b", re.I)
_SMALL = re.compile(r"작은|적은|낮은|적게|최저|최소|\b(?:smallest|lowest|least|fewest)\b", re.I)
MAX_EVIDENCE = 60


def period_group_answer(plan, summary, index, question):
    grains = requested_grains(question) or {
        name for name, pattern in _NOUNS.items() if re.search(pattern, question)}
    if plan is None or len(grains) != 1 or len(plan.group_by) != 1 or plan.having or plan.filter_expression:
        return None
    if plan.operation not in {"numeric_summary", "row_count"} or plan.share_of_total or plan.per_group_limit:
        return None
    tables = [table for table in build_query_tables(summary) if table.id == plan.table_id]
    bound = bind_tabular_plan(plan.model_copy(update={"order_by": None, "limit": None}), tables[0]) if len(tables) == 1 else None
    if bound is None or bound.relative_rank is not None:
        return None
    table, group, grain = tables[0], bound.group_by[0], next(iter(grains))
    measured = list(dict.fromkeys(column for column in bound.column_ids if column != group))
    measure = measured[0] if bound.operation == "numeric_summary" and len(measured) == 1 else None
    statistic = "count" if bound.operation == "row_count" else {"sum": "sum", "all": "sum", "average": "average"}.get(bound.statistic)
    if statistic is None or (statistic != "count" and measure is None) or not validated_table(table, index, {group, *measured}):
        return None
    dates = [_date(row.values.get(group)) for row in table.rows if row.values.get(group) not in (None, "")]
    if not dates or None in dates or len(set(dates)) == len({_bucket(day, grain) for day in dates}):
        return None  # not a date column, or the dates are already one per period: the plan stands
    buckets = _buckets(filtered_rows(table, bound.filters), group, measure, grain)
    if not buckets:
        return None
    unit = total_unit(table, measure)
    headers = {column.id: column for column in table.columns}
    metric = "행 수" if statistic == "count" else f"‘{headers[measure].display_header}’ {'평균' if statistic == 'average' else '합계'}"
    values = {key: (total / len(rows) if statistic == "average" else total) for key, (total, rows) in buckets.items()}
    ordered = sorted(values)
    listed = ", ".join(f"{_label(key, grain)} {shown_total(values[key], unit)}" for key in ordered)
    lead = ""
    if _TOP.search(question) or _SMALL.search(question):
        best = (min if _SMALL.search(question) else max)(ordered, key=lambda key: values[key])
        tied = [key for key in ordered if values[key] == values[best]]
        if len(tied) > 1:
            lead = f"{', '.join(_label(key, grain) for key in tied)}이 같은 값({shown_total(values[best], unit)})으로 공동입니다. "
        else:
            lead = (f"가장 {'작은' if _SMALL.search(question) else '큰'} {_SUBJECT[grain]} {_label(best, grain)}입니다 "
                    f"({metric} {shown_total(values[best], unit)}). ")
    scope = ", ".join(f"‘{headers[item.column_id].display_header}’ {item.operator} {item.value}"
                      for item in bound.filters if item.column_id in headers) or "조건 없이 전체 행"
    source = {cell.reference: cell for row in index.rows if row.sheet_name == table.sheet_name for cell in row.cells}
    references = [headers[group].header_reference, *([headers[measure].header_reference] if measure else []),
                  *(f"{table.sheet_name}!{column}{number}" for key in ordered for number in buckets[key][1][:2]
                    for column in (group, measure) if column)]
    return QuestionAnswer(
        question=question, answer=f"{lead}{_LABELS[grain]}별 {metric}: {listed}.",
        status=QuestionAnswerStatus.LIMITED, confidence=0.8, selected_tools=["period_group_query"],
        evidence=[_evidence(source[key]) for key in dict.fromkeys(references) if key in source][:MAX_EVIDENCE],
        limitations=[f"‘{headers[group].display_header}’ 열의 날짜를 달력 {_LABELS[grain]} 단위로 묶어 {metric}를 원본 전체 행으로 "
                     f"다시 계산했습니다(적용 조건: {scope}). 기록이 없는 기간은 표시하지 않았습니다."],
        verification=QuestionAnswerVerification(
            level="source_checked",
            checks=["source_values", "calculation", "calendar_period", f"calendar_grain_{grain}",
                    "field_interpretation"],
        ))


def period_request_allows_standard_plan(plan, summary, index, question):
    """Allow the generic tabular route only when it preserves an explicit calendar grain."""
    grains = requested_grains(question)
    if not grains:
        return True
    if plan is None or len(grains) != 1 or len(plan.group_by) != 1 or plan.having or plan.filter_expression:
        return False
    if plan.operation not in {"numeric_summary", "row_count"} or plan.share_of_total or plan.per_group_limit:
        return False
    tables = [table for table in build_query_tables(summary) if table.id == plan.table_id]
    bound = bind_tabular_plan(plan.model_copy(update={"order_by": None, "limit": None}), tables[0]) if len(tables) == 1 else None
    if bound is None or bound.relative_rank is not None:
        return False
    table, group, grain = tables[0], bound.group_by[0], next(iter(grains))
    measured = list(dict.fromkeys(column for column in bound.column_ids if column != group))
    measure = measured[0] if bound.operation == "numeric_summary" and len(measured) == 1 else None
    statistic = "count" if bound.operation == "row_count" else {
        "sum": "sum", "all": "sum", "average": "average"
    }.get(bound.statistic)
    if statistic is None or (statistic != "count" and measure is None):
        return False
    if not validated_table(table, index, {group, *measured}):
        return False
    dates = [_date(row.values.get(group)) for row in table.rows if row.values.get(group) not in (None, "")]
    return bool(dates) and None not in dates and len(set(dates)) == len({_bucket(day, grain) for day in dates})


def _buckets(rows, group, measure, grain):
    if rows is None:
        return None
    totals = defaultdict(lambda: [Decimal(0), []])
    for row in rows:
        day, value = _date(row.values.get(group)), row.values.get(measure) if measure else 1
        if day is None:
            if row.values.get(group) in (None, ""):
                continue
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            if value in (None, ""):
                continue
            return None  # a non-numeric amount is never skipped silently
        totals[_bucket(day, grain)][0] += Decimal(str(value))
        totals[_bucket(day, grain)][1].append(row.row_number)
    return dict(totals)


def _date(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _bucket(day, grain):
    return (day.year, day.month if grain == "month" else (day.month - 1) // 3 + 1 if grain == "quarter" else 0)


def _label(key, grain):
    year, part = key
    return f"{year}년" + (f" {part}월" if grain == "month" else f" {part}분기" if grain == "quarter" else "")
