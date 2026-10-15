"""Verify group labels, numeric endpoints and their source period cells."""

import re

from app.agent.query.comparison_evidence import (
    comparison_change_matches, comparison_header_matches, comparison_values_match,
    matched_comparison_evidence,
)
from app.agent.query.question_dates import question_date_bounds
from app.agent.tools.workbook_comparison_series import _date


def grouped_change_proof(question: str, comparison: dict, metrics: list[dict], available):
    period_refs = [comparison.get(f"{side}_reference") for side in ("start", "end")]
    if not all(isinstance(ref, str) for ref in period_refs) or period_refs[0] == period_refs[1]:
        return None
    if not all(_source_row(reference) for reference in period_refs):
        return None
    periods = [_date(comparison.get(f"{side}_date")) for side in ("start", "end")]
    if any(period is None for period in periods) or periods[0] >= periods[1]:
        return None
    lower, upper = question_date_bounds(question)
    if (lower and periods[0] < lower) or (upper and periods[1] > upper):
        return None
    for reference, expected in zip(period_refs, periods):
        evidence, missing = matched_comparison_evidence([reference], available)
        if missing or not any(_date(item.value) == expected for item in evidence):
            return None
    references, checks = list(period_refs), []
    for metric in metrics:
        values = [metric.get(key) for key in ("start_value", "end_value", "change")]
        if not all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            return None
        headers = metric.get("header_references")
        if not isinstance(headers, list) or not all(isinstance(ref, str) for ref in headers):
            return None
        if not comparison_header_matches(metric["header"], tuple(headers), available):
            return None
        if not comparison_change_matches(*values):
            return None
        references.extend(headers)
        for side, period_ref in zip(("start", "end"), period_refs):
            reference = metric.get(f"{side}_reference")
            if _source_row(reference) != _source_row(period_ref):
                return None
            references.append(reference)
            checks.append((reference, metric[f"{side}_value"]))
    evidence, missing = matched_comparison_evidence(references, available)
    if missing or not evidence or not comparison_values_match(tuple(checks), available):
        return None
    return references, tuple(checks)


def _source_row(reference: object) -> tuple[str, str] | None:
    if not isinstance(reference, str) or "!" not in reference:
        return None
    sheet, address = reference.rsplit("!", 1)
    match = re.fullmatch(r"\$?[A-Za-z]+\$?(\d+)", address)
    return (sheet, match[1]) if match else None
