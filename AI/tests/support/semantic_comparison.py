from typing import Callable, Sequence, TypeVar

from tests.support.semantic_regression_models import (
    SemanticPrediction,
    SheetPrediction,
    UnitPrediction,
)
from tests.support.semantic_regression_report import RegressionIssue

T = TypeVar("T")


def compare_semantic_predictions(
    expected: SemanticPrediction,
    actual: SemanticPrediction,
) -> tuple[RegressionIssue, ...]:
    issues: list[RegressionIssue] = []
    compare_value(
        issues, "workbook_mismatch", "workbook", expected.workbook, actual.workbook
    )
    expected_sheets = index_unique(expected.sheets, lambda sheet: sheet.name, "sheet")
    actual_sheets = index_unique(actual.sheets, lambda sheet: sheet.name, "sheet")
    for name in sorted(expected_sheets.keys() - actual_sheets.keys()):
        issues.append(RegressionIssue("missing_sheet", name, name, None))
    for name in sorted(actual_sheets.keys() - expected_sheets.keys()):
        issues.append(RegressionIssue("unexpected_sheet", name, None, name))
    for name in sorted(expected_sheets.keys() & actual_sheets.keys()):
        expected_sheet = expected_sheets[name]
        actual_sheet = actual_sheets[name]
        compare_value(
            issues,
            "sheet_decision_mismatch",
            name,
            expected_sheet.decision,
            actual_sheet.decision,
        )
        compare_value(
            issues,
            "sheet_role_mismatch",
            name,
            expected_sheet.sheet_role,
            actual_sheet.sheet_role,
        )
        issues.extend(compare_regions(name, expected_sheet, actual_sheet))
    return tuple(issues)


def compare_regions(
    sheet_name: str,
    expected_sheet: SheetPrediction,
    actual_sheet: SheetPrediction,
) -> list[RegressionIssue]:
    issues: list[RegressionIssue] = []
    expected = index_unique(
        expected_sheet.regions, lambda region: region.cell_range, f"region in {sheet_name}"
    )
    actual = index_unique(
        actual_sheet.regions, lambda region: region.cell_range, f"region in {sheet_name}"
    )
    for cell_range in sorted(expected.keys() - actual.keys()):
        issues.append(
            RegressionIssue(
                "missing_region", f"{sheet_name}!{cell_range}", cell_range, None
            )
        )
    for cell_range in sorted(actual.keys() - expected.keys()):
        issues.append(
            RegressionIssue(
                "unexpected_region", f"{sheet_name}!{cell_range}", None, cell_range
            )
        )
    for cell_range in sorted(expected.keys() & actual.keys()):
        location = f"{sheet_name}!{cell_range}"
        expected_region = expected[cell_range]
        actual_region = actual[cell_range]
        compare_value(
            issues,
            "region_role_mismatch",
            location,
            expected_region.role,
            actual_region.role,
        )
        compare_value(
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
                    "region_units_mismatch",
                    location,
                    unit_summary(expected_units),
                    unit_summary(actual_units),
                )
            )
    return issues


def compare_value(
    issues: list[RegressionIssue],
    code: str,
    location: str,
    expected: object,
    actual: object,
) -> None:
    if expected != actual:
        issues.append(RegressionIssue(code, location, str(expected), str(actual)))


def index_unique(
    items: Sequence[T], key: Callable[[T], str], label: str
) -> dict[str, T]:
    indexed: dict[str, T] = {}
    for item in items:
        item_key = key(item)
        if item_key in indexed:
            raise ValueError(f"중복된 {label} 키입니다: {item_key}")
        indexed[item_key] = item
    return indexed


def unit_summary(units: Sequence[UnitPrediction]) -> str:
    if not units:
        return "[]"
    return "[" + ", ".join(
        f"{unit.cell_range}:{unit.unit}:{unit.source}" for unit in units
    ) + "]"
