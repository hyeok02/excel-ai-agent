from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Callable, Mapping, Protocol, Sequence, TypeVar

from app.services.semantic_models import SemanticRole


T = TypeVar("T")


@dataclass(frozen=True, order=True)
class UnitPrediction:
    cell_range: str
    unit: str
    source: str


@dataclass(frozen=True)
class RegionPrediction:
    cell_range: str
    role: SemanticRole
    decision: str
    units: tuple[UnitPrediction, ...] = ()


@dataclass(frozen=True)
class SheetPrediction:
    name: str
    decision: str
    sheet_role: str
    regions: tuple[RegionPrediction, ...]


@dataclass(frozen=True)
class SemanticPrediction:
    workbook: str
    sheets: tuple[SheetPrediction, ...]

    @classmethod
    def from_mapping(cls, payload: Mapping[str, object]) -> SemanticPrediction:
        try:
            sheets = tuple(
                SheetPrediction(
                    name=str(sheet["name"]),
                    decision=str(sheet["decision"]),
                    sheet_role=str(sheet["sheet_role"]),
                    regions=tuple(
                        RegionPrediction(
                            cell_range=str(region["range"]),
                            role=SemanticRole(str(region["role"])),
                            decision=str(region["decision"]),
                            units=tuple(
                                UnitPrediction(
                                    cell_range=str(unit["range"]),
                                    unit=str(unit["unit"]),
                                    source=str(unit["source"]),
                                )
                                for unit in region.get("units", [])
                            ),
                        )
                        for region in sheet["regions"]
                    ),
                )
                for sheet in payload["sheets"]
            )
            return cls(workbook=str(payload["workbook"]), sheets=sheets)
        except (KeyError, TypeError) as exception:
            raise ValueError(
                "의미 분석 결과 JSON 형식이 올바르지 않습니다."
            ) from exception


@dataclass(frozen=True)
class SemanticFixtureCase:
    workbook_path: Path
    expectation_path: Path
    coverage: tuple[str, ...]
    expected: SemanticPrediction

    @property
    def name(self) -> str:
        return self.workbook_path.name


class SemanticPredictor(Protocol):
    def predict(self, workbook_path: Path) -> SemanticPrediction:
        """Return semantic labels for one workbook."""


@dataclass(frozen=True)
class RegressionIssue:
    code: str
    location: str
    expected: str | None
    actual: str | None

    def describe(self) -> str:
        values = []
        if self.expected is not None:
            values.append(f"expected={self.expected}")
        if self.actual is not None:
            values.append(f"actual={self.actual}")
        suffix = f" ({', '.join(values)})" if values else ""
        return f"[{self.code}] {self.location}{suffix}"


@dataclass(frozen=True)
class FixtureRegressionResult:
    fixture: str
    issues: tuple[RegressionIssue, ...]

    @property
    def passed(self) -> bool:
        return not self.issues


@dataclass(frozen=True)
class SemanticRegressionReport:
    results: tuple[FixtureRegressionResult, ...]

    @property
    def passed(self) -> bool:
        return all(result.passed for result in self.results)

    @property
    def passed_count(self) -> int:
        return sum(result.passed for result in self.results)

    @property
    def failed_count(self) -> int:
        return len(self.results) - self.passed_count

    def failure_message(self) -> str:
        lines = [
            "Excel 의미 분석 회귀 테스트 실패",
            f"통과 {self.passed_count}개 / 실패 {self.failed_count}개",
        ]
        for result in self.results:
            if result.passed:
                continue
            lines.append(f"- {result.fixture}")
            lines.extend(f"  - {issue.describe()}" for issue in result.issues)
        return "\n".join(lines)

    def assert_passed(self) -> None:
        if not self.passed:
            raise AssertionError(self.failure_message())


class JsonDirectoryPredictor:
    """Load semantic predictions written as `<workbook stem>.actual.json`."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def predict(self, workbook_path: Path) -> SemanticPrediction:
        prediction_path = self.directory / f"{workbook_path.stem}.actual.json"
        with prediction_path.open(encoding="utf-8") as file:
            payload = json.load(file)
        return SemanticPrediction.from_mapping(payload)


def load_semantic_fixture_cases(directory: Path) -> tuple[SemanticFixtureCase, ...]:
    manifest_path = directory / "manifest.json"
    with manifest_path.open(encoding="utf-8") as file:
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
            expectation = json.load(file)
        expected = SemanticPrediction.from_mapping(expectation)
        if expected.workbook != workbook_path.name:
            raise ValueError(
                "fixture 파일명과 기대 결과가 일치하지 않습니다: "
                f"{workbook_path.name}"
            )

        cases.append(
            SemanticFixtureCase(
                workbook_path=workbook_path,
                expectation_path=expectation_path,
                coverage=tuple(fixture.get("coverage", [])),
                expected=expected,
            )
        )
    return tuple(cases)


def run_semantic_regression(
    cases: Sequence[SemanticFixtureCase],
    predictor: SemanticPredictor,
) -> SemanticRegressionReport:
    results = []
    for case in cases:
        try:
            actual = predictor.predict(case.workbook_path)
            issues = compare_semantic_predictions(case.expected, actual)
        except Exception as exception:  # noqa: BLE001 - fixture별 실패를 계속 수집
            issues = (
                RegressionIssue(
                    code="execution_error",
                    location=case.name,
                    expected=None,
                    actual=f"{type(exception).__name__}: {exception}",
                ),
            )
        results.append(FixtureRegressionResult(fixture=case.name, issues=issues))
    return SemanticRegressionReport(results=tuple(results))


def compare_semantic_predictions(
    expected: SemanticPrediction,
    actual: SemanticPrediction,
) -> tuple[RegressionIssue, ...]:
    issues: list[RegressionIssue] = []
    if expected.workbook != actual.workbook:
        issues.append(
            RegressionIssue(
                code="workbook_mismatch",
                location="workbook",
                expected=expected.workbook,
                actual=actual.workbook,
            )
        )

    expected_sheets = _index_unique(expected.sheets, lambda sheet: sheet.name, "sheet")
    actual_sheets = _index_unique(actual.sheets, lambda sheet: sheet.name, "sheet")

    for name in sorted(expected_sheets.keys() - actual_sheets.keys()):
        issues.append(
            RegressionIssue("missing_sheet", name, expected=name, actual=None)
        )
    for name in sorted(actual_sheets.keys() - expected_sheets.keys()):
        issues.append(
            RegressionIssue("unexpected_sheet", name, expected=None, actual=name)
        )

    for name in sorted(expected_sheets.keys() & actual_sheets.keys()):
        expected_sheet = expected_sheets[name]
        actual_sheet = actual_sheets[name]
        _compare_value(
            issues,
            "sheet_decision_mismatch",
            name,
            expected_sheet.decision,
            actual_sheet.decision,
        )
        _compare_value(
            issues,
            "sheet_role_mismatch",
            name,
            expected_sheet.sheet_role,
            actual_sheet.sheet_role,
        )
        issues.extend(_compare_regions(name, expected_sheet, actual_sheet))

    return tuple(issues)


def _compare_regions(
    sheet_name: str,
    expected_sheet: SheetPrediction,
    actual_sheet: SheetPrediction,
) -> list[RegressionIssue]:
    issues: list[RegressionIssue] = []
    expected_regions = _index_unique(
        expected_sheet.regions,
        lambda region: region.cell_range,
        f"region in {sheet_name}",
    )
    actual_regions = _index_unique(
        actual_sheet.regions,
        lambda region: region.cell_range,
        f"region in {sheet_name}",
    )

    for cell_range in sorted(expected_regions.keys() - actual_regions.keys()):
        issues.append(
            RegressionIssue(
                "missing_region",
                f"{sheet_name}!{cell_range}",
                expected=cell_range,
                actual=None,
            )
        )
    for cell_range in sorted(actual_regions.keys() - expected_regions.keys()):
        issues.append(
            RegressionIssue(
                "unexpected_region",
                f"{sheet_name}!{cell_range}",
                expected=None,
                actual=cell_range,
            )
        )

    for cell_range in sorted(expected_regions.keys() & actual_regions.keys()):
        location = f"{sheet_name}!{cell_range}"
        expected_region = expected_regions[cell_range]
        actual_region = actual_regions[cell_range]
        _compare_value(
            issues,
            "region_role_mismatch",
            location,
            expected_region.role,
            actual_region.role,
        )
        _compare_value(
            issues,
            "region_decision_mismatch",
            location,
            expected_region.decision,
            actual_region.decision,
        )
        expected_units = sorted(expected_region.units)
        actual_units = sorted(actual_region.units)
        if expected_units != actual_units:
            issues.append(
                RegressionIssue(
                    code="region_units_mismatch",
                    location=location,
                    expected=_unit_summary(expected_units),
                    actual=_unit_summary(actual_units),
                )
            )
    return issues


def _compare_value(
    issues: list[RegressionIssue],
    code: str,
    location: str,
    expected: str,
    actual: str,
) -> None:
    if expected != actual:
        issues.append(RegressionIssue(code, location, expected, actual))


def _index_unique(
    items: Sequence[T], key: Callable[[T], str], label: str
) -> dict[str, T]:
    indexed: dict[str, T] = {}
    for item in items:
        item_key = key(item)
        if item_key in indexed:
            raise ValueError(f"중복된 {label} 키입니다: {item_key}")
        indexed[item_key] = item
    return indexed


def _unit_summary(units: Sequence[UnitPrediction]) -> str:
    if not units:
        return "[]"
    return (
        "["
        + ", ".join(
            f"{unit.cell_range}:{unit.unit}:{unit.source}" for unit in units
        )
        + "]"
    )
