from dataclasses import replace
import json
from pathlib import Path

import pytest

from tests.run_semantic_regression import main
from tests.support.semantic_regression import (
    RegionPrediction,
    SemanticFixtureCase,
    SemanticPrediction,
    compare_semantic_predictions,
    load_semantic_fixture_cases,
    run_semantic_regression,
)


FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "semantic"


class ExpectedPredictionProvider:
    def __init__(self, cases: tuple[SemanticFixtureCase, ...]) -> None:
        self.predictions = {case.name: case.expected for case in cases}

    def predict(self, workbook_path: Path) -> SemanticPrediction:
        return self.predictions[workbook_path.name]


class FailingPredictionProvider(ExpectedPredictionProvider):
    def __init__(
        self,
        cases: tuple[SemanticFixtureCase, ...],
        failing_fixture: str,
    ) -> None:
        super().__init__(cases)
        self.failing_fixture = failing_fixture

    def predict(self, workbook_path: Path) -> SemanticPrediction:
        if workbook_path.name == self.failing_fixture:
            raise RuntimeError("분석기 호출 실패")
        return super().predict(workbook_path)


def test_loads_semantic_cases_in_manifest_order() -> None:
    cases = load_semantic_fixture_cases(FIXTURE_DIRECTORY)

    assert [case.name for case in cases] == [
        "semantic_simple_table.xlsx",
        "semantic_hierarchical_headers.xlsx",
        "semantic_mixed_regions.xlsx",
    ]
    assert all(case.coverage for case in cases)
    assert sum(len(case.expected.sheets) for case in cases) == 5


def test_regression_runner_passes_matching_predictions() -> None:
    cases = load_semantic_fixture_cases(FIXTURE_DIRECTORY)

    report = run_semantic_regression(cases, ExpectedPredictionProvider(cases))

    assert report.passed is True
    assert report.passed_count == 3
    assert report.failed_count == 0
    report.assert_passed()


def test_comparator_reports_semantic_label_differences() -> None:
    case = load_semantic_fixture_cases(FIXTURE_DIRECTORY)[0]
    expected_sheet = case.expected.sheets[0]
    changed_regions = list(expected_sheet.regions)
    changed_regions[0] = replace(
        changed_regions[0],
        role="data",
        decision="analyze",
    )
    changed_regions[3] = replace(changed_regions[3], units=())
    changed_regions.pop(1)
    changed_regions.append(
        RegionPrediction(
            cell_range="F1:F2",
            role="warning",
            decision="context",
        )
    )
    actual = replace(
        case.expected,
        sheets=(
            replace(
                expected_sheet,
                decision="metadata_only",
                sheet_role="instruction",
                regions=tuple(changed_regions),
            ),
        ),
    )

    issues = compare_semantic_predictions(case.expected, actual)
    issue_codes = {issue.code for issue in issues}

    assert issue_codes == {
        "sheet_decision_mismatch",
        "sheet_role_mismatch",
        "missing_region",
        "unexpected_region",
        "region_role_mismatch",
        "region_decision_mismatch",
        "region_units_mismatch",
    }
    assert any(issue.location == "월별 매출!A1:D1" for issue in issues)


def test_regression_runner_collects_execution_errors_and_continues() -> None:
    cases = load_semantic_fixture_cases(FIXTURE_DIRECTORY)
    predictor = FailingPredictionProvider(cases, "semantic_hierarchical_headers.xlsx")

    report = run_semantic_regression(cases, predictor)

    assert report.passed is False
    assert report.passed_count == 2
    assert report.failed_count == 1
    assert report.results[1].issues[0].code == "execution_error"
    assert "semantic_hierarchical_headers.xlsx" in report.failure_message()
    assert "RuntimeError: 분석기 호출 실패" in report.failure_message()
    with pytest.raises(AssertionError, match="회귀 테스트 실패"):
        report.assert_passed()


def test_cli_compares_actual_json_directory(tmp_path: Path, capsys: object) -> None:
    cases = load_semantic_fixture_cases(FIXTURE_DIRECTORY)
    for case in cases:
        payload = json.loads(case.expectation_path.read_text(encoding="utf-8"))
        actual_path = tmp_path / f"{case.workbook_path.stem}.actual.json"
        actual_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )

    exit_code = main(["--actual-dir", str(tmp_path)])

    assert exit_code == 0
    assert "회귀 테스트 통과: 3개" in capsys.readouterr().out


def test_cli_returns_failure_when_actual_json_is_missing(
    tmp_path: Path,
    capsys: object,
) -> None:
    exit_code = main(["--actual-dir", str(tmp_path)])

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "통과 0개 / 실패 3개" in output
    assert "execution_error" in output
