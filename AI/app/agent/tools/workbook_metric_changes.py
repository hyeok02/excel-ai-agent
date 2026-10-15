"""질문이 이름을 댄 항목 하나의 변화를 고른다."""
import re

from app.agent.tools.workbook_metric_matching import (
    complete_metric,
    contains_term,
    unique_named_metric,
)
from app.agent.tools.workbook_metric_periods import build_metric_period
from app.agent.tools.workbook_metric_snapshots import build_metric_snapshot

COUNT_WORDS = ("개수", "건수", "how many", "count")
COUNT_PATTERN = re.compile(r"(?:몇|총)\s*(?:개|가지|종류)")
AGGREGATE_WORDS = (
    "평균", "최고", "최대", "최저", "최소", "가장", "제일", "average",
    "mean", "maximum", "minimum", "highest", "lowest",
)
CHANGE_WORDS = (
    "변화", "변동", "증감", "추이", "비교", "감소", "증가",
    "변했", "달라", "줄어", "줄었", "늘어", "늘었", "change", "trend",
    "compare", "decreas", "increas", "grew", "fell",
)
DATE_WORD = re.compile(r"(?<!\d)20\d{2}(?!\d)|(?<!\d)\d{1,2}\s*월")
GROUP_NAMES = {"department": "부서", "role": "직무"}


def comparison_payload(comparison: object, question: str, intent) -> dict[str, object]:
    targets = tuple(getattr(intent, "targets", ()) or ())
    kind = str(getattr(intent, "kind", "") or "")
    specific = not bool(getattr(intent, "whole_workbook", False))
    return {
        "time_series_comparison": comparison,
        "metric_period": build_metric_period(comparison, question) if specific else None,
        "metric_snapshot": build_metric_snapshot(comparison, question, targets)
        if specific
        else None,
        "named_metric_change": build_metric_change(
            comparison, question, targets, allow_implicit=kind == "comparison"
        )
        if specific
        else None,
        "metric_count": build_metric_count(comparison, question)
        if specific
        else None,
        "answer_kind": kind,
        "answer_scope": "specific" if specific else "whole_workbook",
    }


def build_metric_count(comparison: object, question: str) -> dict[str, object] | None:
    if not isinstance(comparison, dict):
        return None
    group = GROUP_NAMES.get(str(comparison.get("metric_group")))
    normalized = question.casefold()
    if not group or group not in normalized:
        return None
    if not (
        any(contains_term(normalized, word) for word in COUNT_WORDS)
        or COUNT_PATTERN.search(normalized)
    ):
        return None
    metrics = comparison.get("metrics")
    if not isinstance(metrics, list):
        return None
    counted = [
        metric for metric in metrics
        if isinstance(metric, dict) and complete_metric(metric)
    ]
    if not counted:
        return None
    return {
        "group": group,
        "count": len(counted),
        "names": [str(metric["header"]) for metric in counted],
        "references": list(dict.fromkeys(
            value for metric in counted
            for value in metric.get("header_references") or ()
            if isinstance(value, str)
        )),
    }


def build_metric_change(
    comparison: object,
    question: str,
    targets: tuple[str, ...] = (),
    allow_implicit: bool = False,
) -> dict[str, object] | None:
    if not isinstance(comparison, dict):
        return None
    start_reference = comparison.get("start_reference")
    if isinstance(start_reference, str) and start_reference == comparison.get("end_reference"):
        return None
    normalized = question.casefold()
    asks_for_change = any(word in normalized for word in CHANGE_WORDS)
    if not allow_implicit and not asks_for_change:
        return None
    if any(contains_term(normalized, word) for word in AGGREGATE_WORDS):
        return None
    if DATE_WORD.search(normalized) and not asks_for_change:
        return None
    metrics = comparison.get("metrics")
    if not isinstance(metrics, list):
        return None
    metric = unique_named_metric(metrics, question, targets)
    if metric is None:
        return None
    return {
        "sheet_name": comparison.get("sheet_name"),
        "header": metric["header"],
        "header_references": [
            value for value in metric.get("header_references") or ()
            if isinstance(value, str)
        ],
        "start_value": metric["start_value"],
        "end_value": metric["end_value"],
        "change": metric["change"],
        "start_number_format": metric.get("start_number_format"),
        "end_number_format": metric.get("end_number_format"),
        "start_reference": metric["start_reference"],
        "end_reference": metric["end_reference"],
        "period_references": [
            value
            for key in ("start_reference", "end_reference")
            if isinstance(value := comparison.get(key), str)
        ],
        "start_date": metric.get("start_date") or comparison.get("start_date"),
        "end_date": comparison.get("end_date"),
        "metric_group": comparison.get("metric_group"),
    }
