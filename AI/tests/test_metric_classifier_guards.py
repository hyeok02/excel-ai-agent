from types import SimpleNamespace

from app.agent.tools.workbook_metric_changes import (
    build_metric_change,
    comparison_payload,
)
from app.agent.tools.workbook_metric_snapshots import build_metric_snapshot


def test_metric_name_containing_change_syllable_is_still_a_snapshot() -> None:
    comparison = _comparison("늘봄점")

    assert build_metric_change(comparison, "늘봄점 값 알려줘") is None
    assert build_metric_snapshot(comparison, "늘봄점 값 알려줘") is not None


def test_wrong_kind_cannot_hide_an_explicit_change() -> None:
    whole = SimpleNamespace(
        whole_workbook=True, kind="comparison", targets=("Services",)
    )
    unrelated = SimpleNamespace(
        whole_workbook=False, kind="structure", targets=("Services",)
    )

    assert comparison_payload(_comparison(), "Services 변화", whole)[
        "named_metric_change"
    ] is None
    found = comparison_payload(_comparison(), "Services 변화", unrelated)
    assert found["named_metric_change"]["header"] == "Services"


def test_wrong_kind_cannot_hide_an_explicit_snapshot() -> None:
    intent = SimpleNamespace(
        whole_workbook=False, kind="summary", targets=("Services",)
    )

    found = comparison_payload(_comparison(), "Services 최신 값", intent)

    assert found["metric_snapshot"]["metrics"][0]["header"] == "Services"


def _comparison(header: str = "Services") -> dict:
    return {
        "sheet_name": "Metrics",
        "metric_group": "department",
        "start_date": "2023-01-01",
        "end_date": "2025-01-01",
        "start_reference": "Metrics!A2",
        "end_reference": "Metrics!A4",
        "metrics": [{
            "header": header,
            "start_value": 10,
            "end_value": 12,
            "change": 2.0,
            "header_references": ["Metrics!B1"],
            "start_reference": "Metrics!B2",
            "end_reference": "Metrics!B4",
        }],
    }
