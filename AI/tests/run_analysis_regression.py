from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from tests.support.analysis_regression import (
    WorkbookAnalysisPredictor,
    load_analysis_fixture_cases,
    run_analysis_regression,
)

DEFAULT_FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "analysis"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="도메인이 다른 워크북에서 분석 판정이 유지되는지 확인"
    )
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=DEFAULT_FIXTURE_DIRECTORY,
        help="manifest.json이 있는 analysis fixture 디렉터리",
    )
    arguments = parser.parse_args(argv)

    cases = load_analysis_fixture_cases(arguments.fixture_dir)
    report = run_analysis_regression(cases, WorkbookAnalysisPredictor())
    if not report.passed:
        print(report.failure_message())
        return 1

    print(f"Excel 분석 판정 회귀 테스트 통과: {report.passed_count}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
