from __future__ import annotations

from collections.abc import Sequence

from tests.support.analysis_comparison import compare_analysis_predictions
from tests.support.analysis_regression_models import (
    AnalysisFixtureCase,
    AnalysisPredictor,
)
from tests.support.semantic_regression_report import (
    FixtureRegressionResult,
    RegressionIssue,
    SemanticRegressionReport,
)

REPORT_TITLE = "Excel 분석 판정 회귀 테스트"


def run_analysis_regression(
    cases: Sequence[AnalysisFixtureCase],
    predictor: AnalysisPredictor,
) -> SemanticRegressionReport:
    results = []
    for case in cases:
        try:
            actual = predictor.predict(case)
            issues = compare_analysis_predictions(case.expected, actual)
        except Exception as exception:  # noqa: BLE001
            issues = (
                RegressionIssue(
                    "execution_error",
                    case.name,
                    None,
                    f"{type(exception).__name__}: {exception}",
                ),
            )
        results.append(FixtureRegressionResult(case.name, issues))
    return SemanticRegressionReport(tuple(results), REPORT_TITLE)
