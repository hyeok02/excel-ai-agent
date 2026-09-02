import json
from pathlib import Path

from tests.support.analysis_regression import (
    WorkbookAnalysisPredictor,
    load_analysis_fixture_cases,
    run_analysis_regression,
)

FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "analysis"


def test_manifest_and_expectations_are_complete() -> None:
    manifest = json.loads(
        (FIXTURE_DIRECTORY / "manifest.json").read_text(encoding="utf-8")
    )

    assert manifest["schema_version"] == 1
    assert len(manifest["fixtures"]) >= 4
    for fixture in manifest["fixtures"]:
        assert fixture["coverage"]
        assert (FIXTURE_DIRECTORY / fixture["workbook"]).is_file()
        assert (FIXTURE_DIRECTORY / fixture["expectation"]).is_file()


def test_fixtures_cover_more_than_one_domain_shape() -> None:
    """구조만 다른 픽스처는 도메인 종속을 잡아내지 못한다."""
    cases = load_analysis_fixture_cases(FIXTURE_DIRECTORY)
    coverage = {tag for case in cases for tag in case.coverage}

    assert {"no_identity_row", "no_time_series", "english_only"} <= coverage


def test_analysis_verdicts_hold_across_domains() -> None:
    cases = load_analysis_fixture_cases(FIXTURE_DIRECTORY)

    report = run_analysis_regression(cases, WorkbookAnalysisPredictor())

    report.assert_passed()
    assert report.passed_count == len(cases)
