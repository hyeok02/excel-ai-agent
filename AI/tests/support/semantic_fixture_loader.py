import json
from pathlib import Path

from tests.support.semantic_regression_models import (
    SemanticFixtureCase,
    SemanticPrediction,
)


def load_semantic_fixture_cases(directory: Path) -> tuple[SemanticFixtureCase, ...]:
    with (directory / "manifest.json").open(encoding="utf-8") as file:
        manifest = json.load(file)
    if manifest.get("schema_version") != 1:
        raise ValueError("지원하지 않는 의미 분석 fixture manifest 버전입니다.")
    fixtures = manifest.get("fixtures")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("의미 분석 fixture manifest에 실행 대상이 없습니다.")
    cases = []
    workbook_names: set[str] = set()
    for fixture in fixtures:
        workbook_path = directory / fixture["workbook"]
        expectation_path = directory / fixture["expectation"]
        if workbook_path.name in workbook_names:
            raise ValueError(f"중복된 fixture입니다: {workbook_path.name}")
        workbook_names.add(workbook_path.name)
        if not workbook_path.is_file():
            raise FileNotFoundError(workbook_path)
        if not expectation_path.is_file():
            raise FileNotFoundError(expectation_path)
        with expectation_path.open(encoding="utf-8") as file:
            expected = SemanticPrediction.from_mapping(json.load(file))
        if expected.workbook != workbook_path.name:
            raise ValueError(
                f"fixture 파일명과 기대 결과가 일치하지 않습니다: {workbook_path.name}"
            )
        cases.append(
            SemanticFixtureCase(
                workbook_path,
                expectation_path,
                tuple(fixture.get("coverage", [])),
                expected,
            )
        )
    return tuple(cases)


class JsonDirectoryPredictor:
    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def predict(self, workbook_path: Path) -> SemanticPrediction:
        path = self.directory / f"{workbook_path.stem}.actual.json"
        with path.open(encoding="utf-8") as file:
            return SemanticPrediction.from_mapping(json.load(file))
