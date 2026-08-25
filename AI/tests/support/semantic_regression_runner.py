from collections.abc import Sequence

from tests.support.semantic_comparison import compare_semantic_predictions
from tests.support.semantic_regression_models import (
    SemanticFixtureCase,
    SemanticPredictor,
)
from tests.support.semantic_regression_report import (
    FixtureRegressionResult,
    RegressionIssue,
    SemanticRegressionReport,
)


def run_semantic_regression(
    cases: Sequence[SemanticFixtureCase],
    predictor: SemanticPredictor,
) -> SemanticRegressionReport:
    results = []
    for case in cases:
        try:
            actual = predictor.predict(case.workbook_path)
            issues = compare_semantic_predictions(case.expected, actual)
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
    return SemanticRegressionReport(tuple(results))
