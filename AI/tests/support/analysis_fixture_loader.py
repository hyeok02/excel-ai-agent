from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

from tests.support.analysis_regression_models import (
    AnalysisFixtureCase,
    AnalysisPrediction,
    MetricChange,
)


def load_analysis_fixture_cases(
    directory: Path,
) -> tuple[AnalysisFixtureCase, ...]:
    manifest = _load_json(directory / "manifest.json")
    if manifest.get("schema_version") != 1:
        raise ValueError("지원하지 않는 manifest schema_version 입니다.")
    return tuple(
        _build_case(directory, entry) for entry in manifest["fixtures"]
    )


def _build_case(
    directory: Path, entry: Mapping[str, object]
) -> AnalysisFixtureCase:
    workbook = str(entry["workbook"])
    expectation = _load_json(directory / str(entry["expectation"]))
    if expectation.get("workbook") != workbook:
        raise ValueError(f"기대 결과의 workbook 이름이 다릅니다: {workbook}")
    review_points = expectation["review_points"]
    questions = expectation["questions"]
    prediction = AnalysisPrediction(
        workbook=workbook,
        subject=expectation["subject"],
        changes=tuple(
            MetricChange.from_mapping(item)
            for item in expectation["numeric_changes"]
        ),
        review_points={
            str(item["impact"]): str(item["verdict"]) for item in review_points
        },
        questions={
            str(item["question"]): str(item["verdict"]) for item in questions
        },
    )
    return AnalysisFixtureCase(
        name=workbook,
        workbook_path=directory / workbook,
        expected=prediction,
        coverage=tuple(str(item) for item in entry.get("coverage", ())),
        review_point_texts=tuple(str(item["impact"]) for item in review_points),
        question_texts=tuple(str(item["question"]) for item in questions),
    )


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
