import pytest

from app.agent.tools.workbook_metric_snapshots import build_metric_snapshot


@pytest.mark.parametrize(
    ("header", "question"),
    (("Consumption", "latest Consumption"), ("Total Employees", "latest headcount")),
)
def test_metric_names_containing_aggregate_substrings_are_not_blocked(
    header: str, question: str
) -> None:
    snapshot = build_metric_snapshot(_comparison([header]), question)

    assert snapshot is not None and snapshot["metrics"][0]["header"] == header


def test_grouped_snapshot_does_not_ignore_an_extra_condition() -> None:
    comparison = _comparison(["R&D", "Sales"])
    comparison["metric_group"] = "department"

    assert build_metric_snapshot(
        comparison, "부서별 직원 수 for supplier A"
    ) is None


def test_grouped_snapshot_narrows_to_a_named_metric() -> None:
    comparison = _comparison(["R&D", "Sales"])
    comparison["metric_group"] = "department"

    snapshot = build_metric_snapshot(comparison, "부서별 R&D 직원 수 최신값")

    assert snapshot is not None
    assert [item["header"] for item in snapshot["metrics"]] == ["R&D"]


def test_year_only_question_reads_a_single_year_observation() -> None:
    comparison = _comparison(["Revenue"])
    comparison.update(
        start_date="2024-01-01", end_date="2024-01-01", observation_count=1
    )
    comparison["metrics"][0].update(start_value=12, change=0)

    snapshot = build_metric_snapshot(comparison, "2024년 Revenue 값은?")

    assert snapshot is not None
    assert snapshot["metrics"][0]["value"] == 12


def test_year_only_question_does_not_choose_among_multiple_observations() -> None:
    comparison = _comparison(["Revenue"])
    comparison.update(observation_count=2)

    assert build_metric_snapshot(comparison, "2025년 Revenue 값은?") is None


def _comparison(headers: list[str]) -> dict:
    return {
        "sheet_name": "Metrics",
        "start_date": "2025-01-01",
        "end_date": "2025-06-01",
        "start_reference": "Metrics!A2",
        "end_reference": "Metrics!A3",
        "metrics": [_metric(header, index) for index, header in enumerate(headers, 2)],
    }


def _metric(header: str, column: int) -> dict:
    letter = chr(64 + column)
    return {
        "header": header,
        "start_value": 10,
        "end_value": 12,
        "change": 2,
        "header_references": [f"Metrics!{letter}1"],
        "start_reference": f"Metrics!{letter}2",
        "end_reference": f"Metrics!{letter}3",
    }
