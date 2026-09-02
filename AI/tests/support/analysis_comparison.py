from __future__ import annotations

import math
from typing import Mapping

from tests.support.analysis_regression_models import AnalysisPrediction
from tests.support.semantic_regression_report import RegressionIssue

TOLERANCE = 1e-6


def compare_analysis_predictions(
    expected: AnalysisPrediction, actual: AnalysisPrediction
) -> tuple[RegressionIssue, ...]:
    issues = list(_compare_subject(expected, actual))
    issues.extend(_compare_changes(expected, actual))
    issues.extend(
        _compare_verdicts(
            "review_point_verdict_mismatch",
            expected.workbook,
            expected.review_points,
            actual.review_points,
        )
    )
    issues.extend(
        _compare_verdicts(
            "question_verdict_mismatch",
            expected.workbook,
            expected.questions,
            actual.questions,
        )
    )
    return tuple(issues)


def _compare_subject(expected, actual):
    if expected.subject != actual.subject:
        yield RegressionIssue(
            "subject_mismatch",
            expected.workbook,
            repr(expected.subject),
            repr(actual.subject),
        )


def _compare_changes(expected, actual):
    expected_by_metric = {item.metric: item for item in expected.changes}
    actual_by_metric = {item.metric: item for item in actual.changes}
    for metric in expected_by_metric.keys() - actual_by_metric.keys():
        yield RegressionIssue("missing_change", f"{expected.workbook}:{metric}", metric, None)
    for metric in actual_by_metric.keys() - expected_by_metric.keys():
        yield RegressionIssue("unexpected_change", f"{expected.workbook}:{metric}", None, metric)
    for metric in expected_by_metric.keys() & actual_by_metric.keys():
        yield from _compare_change_fields(
            expected.workbook, expected_by_metric[metric], actual_by_metric[metric]
        )
    if expected_by_metric.keys() == actual_by_metric.keys():
        expected_order = [item.metric for item in expected.changes]
        actual_order = [item.metric for item in actual.changes]
        if expected_order != actual_order:
            yield RegressionIssue(
                "change_order_mismatch",
                expected.workbook,
                ", ".join(expected_order),
                ", ".join(actual_order),
            )


def _compare_change_fields(workbook: str, expected, actual):
    for field, expected_value in expected.fields().items():
        actual_value = actual.fields()[field]
        if _differs(expected_value, actual_value):
            yield RegressionIssue(
                "change_field_mismatch",
                f"{workbook}:{expected.metric}.{field}",
                str(expected_value),
                str(actual_value),
            )


def _differs(expected_value: object, actual_value: object) -> bool:
    if isinstance(expected_value, float) and isinstance(actual_value, float):
        return not math.isclose(expected_value, actual_value, abs_tol=TOLERANCE)
    return expected_value != actual_value


def _compare_verdicts(
    code: str,
    workbook: str,
    expected: Mapping[str, str],
    actual: Mapping[str, str],
):
    for key, expected_verdict in expected.items():
        actual_verdict = actual.get(key)
        if actual_verdict != expected_verdict:
            yield RegressionIssue(
                code, f"{workbook}: {key}", expected_verdict, actual_verdict
            )
