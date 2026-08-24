from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from tests.support.semantic_regression import (
    JsonDirectoryPredictor,
    load_semantic_fixture_cases,
    run_semantic_regression,
)


DEFAULT_FIXTURE_DIRECTORY = Path(__file__).parent / "fixtures" / "semantic"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Excel 의미 분석 actual JSON을 fixture 기대 결과와 비교"
    )
    parser.add_argument(
        "--actual-dir",
        type=Path,
        required=True,
        help="<workbook stem>.actual.json 파일이 있는 디렉터리",
    )
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=DEFAULT_FIXTURE_DIRECTORY,
        help="manifest.json이 있는 semantic fixture 디렉터리",
    )
    arguments = parser.parse_args(argv)

    cases = load_semantic_fixture_cases(arguments.fixture_dir)
    report = run_semantic_regression(
        cases,
        JsonDirectoryPredictor(arguments.actual_dir),
    )
    if not report.passed:
        print(report.failure_message())
        return 1

    print(f"Excel 의미 분석 회귀 테스트 통과: {report.passed_count}개")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
