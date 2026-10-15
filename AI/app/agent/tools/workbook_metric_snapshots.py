"""Build a latest-value answer candidate from a verified time series."""

import re
from app.agent.query.question_dates import requested_calendar_period
from app.agent.tools.workbook_metric_matching import (
    complete_metric,
    contains_term,
    has_extra_metric_identity,
    unique_named_metric,
)

GROUP_NAMES = {"department": "부서", "role": "직무"}
GROUP_MARKERS = ("항목별", "부서별", "직무별", "각 부서", "각 직무", "by department", "by role")
BLOCKING_WORDS = (
    "변화", "변동", "증감", "추이", "비교", "감소", "증가", "줄어", "줄었",
    "늘어", "늘었",
    "평균", "중앙값", "합계", "총합", "최고", "최대", "최저", "최소",
    "가장", "제일", "몇 개", "몇개", "개수", "건수", "언제", "몇 년",
    "시작", "change", "trend", "compare", "average", "mean", "median",
    "sum", "maximum", "minimum", "highest", "lowest", "how many", "count",
)
DATE_WORD = re.compile(r"(?<!\d)(?:19|20)\d{2}(?!\d)")
RANK_WORD = re.compile(r"(?<!\d)\d+\s*위|\b(?:rank|top)\s*\d+\b", re.I)
EXACT_ENGLISH_BLOCKERS = {"sum", "count", "mean"}


def build_metric_snapshot(
    comparison: object, question: str, targets: tuple[str, ...] = ()
) -> dict[str, object] | None:
    if not isinstance(comparison, dict) or _blocked(question):
        return None
    metrics = comparison.get("metrics")
    if not isinstance(metrics, list):
        return None
    complete = [item for item in metrics if isinstance(item, dict) and complete_metric(item)]
    group = GROUP_NAMES.get(str(comparison.get("metric_group")))
    requested_period = requested_calendar_period(question)
    if DATE_WORD.search(question) and requested_period is None:
        return None
    if requested_period and _ambiguous_month(comparison, requested_period):
        return None
    found = unique_named_metric(metrics, question, targets)
    if found:
        selected = [found]
    elif (
        group and any(marker in question.casefold() for marker in GROUP_MARKERS)
        and not has_extra_metric_identity(question)
    ):
        selected = complete
    else:
        selected = []
    if not selected:
        return None
    side = "start" if requested_period else "end"
    period = comparison.get(f"{side}_date")
    if requested_period and not _period_matches(str(period or ""), requested_period):
        return None
    return {
        "sheet_name": comparison.get("sheet_name"),
        "group": group,
        "end_date": period,
        "period_reference": comparison.get(f"{side}_reference"),
        "metrics": [_snapshot_item(item, side) for item in selected],
    }


def _snapshot_item(metric: dict, side: str) -> dict[str, object]:
    return {
        "header": metric["header"],
        "header_references": [
            value for value in metric.get("header_references") or ()
            if isinstance(value, str)
        ],
        "value": metric[f"{side}_value"],
        "value_reference": metric[f"{side}_reference"],
        "number_format": metric.get(f"{side}_number_format"),
    }


def _blocked(question: str) -> bool:
    normalized = question.casefold()
    return (
        any(
            contains_term(normalized, word)
            if word in EXACT_ENGLISH_BLOCKERS else word in normalized
            for word in BLOCKING_WORDS
        )
        or bool(RANK_WORD.search(normalized))
    )
def _period_matches(
    period: str, requested: tuple[int, int | None, int | None]
) -> bool:
    found = re.match(r"((?:19|20)\d{2})-(\d{2})-(\d{2})", period)
    if not found:
        return False
    year, month, day = (int(value) for value in found.groups())
    return year == requested[0] and (
        requested[1] is None or month == requested[1]
    ) and (
        requested[2] is None or day == requested[2]
    )


def _ambiguous_month(
    comparison: dict[str, object], requested: tuple[int, int | None, int | None]
) -> bool:
    if requested[2] is not None:
        return False
    count = comparison.get("observation_count")
    if isinstance(count, int):
        return count != 1
    start = str(comparison.get("start_date") or "")
    end = str(comparison.get("end_date") or "")
    return start != end and all(
        _period_matches(period, requested) for period in (start, end)
    )
