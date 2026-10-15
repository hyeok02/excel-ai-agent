"""Select all requested metrics without discarding a named condition."""

import re

from app.agent.query.comparison_scope import requested_metric_group
from app.agent.tools.workbook_metric_changes import AGGREGATE_WORDS, CHANGE_WORDS
from app.agent.tools.workbook_metric_matching import (
    complete_metric, contains_term, has_extra_metric_identity, unique_named_metric,
)

GROUP_MARKERS = (
    "항목별", "각 항목", "부서별", "각 부서", "부문별", "각 부문", "직무별", "각 직무",
    "역할별", "각 역할", "by department", "by role", "each department", "each role",
    "by metric", "each metric",
)
ENDPOINT_WORDS = re.compile(
    r"(?:시작|마지막|처음|끝)\s*값(?:으로|과|와|을|를|의)?|기준으로|"
    r"\b비교(?:해줘요|해주세요|해줄래|해줘|해봐)?(?=\s|$|[?.,])|"
    r"\b(?:start(?:ing)?|first|last|end(?:ing)?|final|between|versus|vs)\b",
    re.I,
)


def selected_grouped_changes(question: str, comparison: object) -> list[dict]:
    if not isinstance(comparison, dict):
        return []
    normalized = question.casefold()
    group = requested_metric_group(question)
    if not any(word in normalized for word in CHANGE_WORDS):
        return []
    if not any(word in normalized for word in GROUP_MARKERS):
        return []
    if any(contains_term(normalized, word) for word in AGGREGATE_WORDS):
        return []
    if group and group != comparison.get("metric_group"):
        return []
    metrics = comparison.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        return []
    cleaned = ENDPOINT_WORDS.sub(" ", question)
    for marker in GROUP_MARKERS:
        cleaned = re.sub(re.escape(marker), " ", cleaned, flags=re.I)
    cleaned = re.sub(r"\b(?:departments?|roles?)\b|부서|부문|직무|역할", " ", cleaned, flags=re.I)
    if has_extra_metric_identity(cleaned):
        named = unique_named_metric(metrics, cleaned)
        return [named] if named is not None else []
    # A lone total is not evidence of a departmental breakdown.
    if len(metrics) < 2 or not all(
        isinstance(metric, dict) and complete_metric(metric) for metric in metrics
    ):
        return []
    if len({str(metric["header"]).casefold() for metric in metrics}) != len(metrics):
        return []
    return metrics
