import pytest

from app.agent.query.metric_change_answers import _text
from app.agent.tools.workbook_metric_changes import (
    build_metric_change,
    build_metric_count,
)
from app.agent.tools.workbook_metric_snapshots import build_metric_snapshot
from app.agent.tools.workbook_metric_periods import build_metric_period


@pytest.mark.parametrize(
    "question",
    (
        "Services 평균이 얼마야?",
        "Services 최고 인원은?",
        "Services 2024년 인원 알려줘",
    ),
)
def test_point_or_aggregate_question_is_not_rewritten_as_change(question: str) -> None:
    assert build_metric_change(_comparison(), question, ("Services",)) is None


def test_plain_named_metric_question_is_not_rewritten_as_change() -> None:
    assert build_metric_change(_comparison(), "Services 인원 알려줘") is None
    snapshot = build_metric_snapshot(_comparison(), "Services 인원 알려줘")
    assert snapshot is not None
    assert snapshot["metrics"][0]["header"] == "Services"


def test_grouped_values_use_latest_snapshot_not_a_change_fact() -> None:
    snapshot = build_metric_snapshot(
        _comparison(), "부서 등 항목별 전체 직원 수 알려줘"
    )
    assert snapshot is not None
    assert [item["value"] for item in snapshot["metrics"]] == [8, 7]


@pytest.mark.parametrize(
    "question", ("Services 평균은?", "Services 추이는?")
)
def test_point_aggregate_and_change_questions_are_not_latest_snapshots(
    question: str,
) -> None:
    assert build_metric_snapshot(_comparison(), question) is None


def test_month_lookup_uses_that_month_not_the_latest_value() -> None:
    comparison = _comparison()
    comparison.update(
        start_date="2025-03-31", start_reference="Metrics!A3",
        end_date="2025-06-30", end_reference="Metrics!A6",
    )
    comparison["metrics"] = [_metric("재료비", 4480, 4980, "B")]
    comparison["metrics"][0].update(
        start_reference="Metrics!B3", end_reference="Metrics!B6"
    )

    found = build_metric_snapshot(comparison, "2025년 3월 재료비는?")
    assert found is not None
    assert found["end_date"] == "2025-03-31"
    assert found["metrics"][0]["value"] == 4480


def test_unobserved_month_is_not_replaced_by_a_later_value() -> None:
    assert build_metric_snapshot(_comparison(), "2025년 3월 Services 인원은?") is None


def test_model_comparison_intent_can_supply_an_implicit_change() -> None:
    found = build_metric_change(
        _comparison(), "Services 인원 알려줘", allow_implicit=True
    )

    assert found is not None and found["header"] == "Services"


def test_how_many_years_is_not_mistaken_for_department_count() -> None:
    assert build_metric_count(_comparison(), "부서별 추이는 몇 년부터야?") is None
    assert build_metric_count(_comparison(), "부서가 총 몇 개야?")["count"] == 2
    found = build_metric_period(_comparison(), "부서별 추이는 몇 년부터야?")
    assert found is not None and found["start_date"] == "2023-01-01"


def test_period_by_period_trend_is_not_rewritten_as_the_observed_range() -> None:
    assert build_metric_period(_comparison(), "기간별 추이를 알려줘") is None
    assert build_metric_period(_comparison(), "데이터 기간을 알려줘") is not None


def test_short_english_header_requires_a_token_match() -> None:
    comparison = _comparison()
    comparison["metrics"] = [_metric("IT", 10, 12, "D")]
    assert build_metric_change(comparison, "profit 변화 알려줘") is None
    assert build_metric_change(comparison, "IT 변화 알려줘") is not None


def test_generic_employee_word_does_not_select_total_for_an_unknown_team() -> None:
    comparison = _comparison()
    comparison["metrics"] = [_metric("Total Employees", 10, 12, "D")]

    assert build_metric_change(comparison, "IT 직원 수 변화") is None


def test_zero_change_is_described_as_unchanged_without_inventing_people_unit() -> None:
    found = {
        "header": "Services", "start_value": 10, "end_value": 10,
        "change": 0, "metric_group": "department",
        "start_date": "2024-01-01", "end_date": "2024-12-01",
    }

    text = _text("Services 변화 알려줘", found)

    assert "변동이 없었습니다" in text
    assert "증가" not in text
    assert "명" not in text


def _comparison() -> dict:
    return {
        "sheet_name": "Metrics", "metric_group": "department",
        "start_date": "2023-01-01", "end_date": "2025-01-01",
        "start_reference": "Metrics!A2", "end_reference": "Metrics!A4",
        "metrics": [
            _metric("Services", 10, 8, "B"),
            _metric("Research & Development", 5, 7, "C"),
        ],
    }


def _metric(header: str, start: int, end: int, column: str) -> dict:
    return {
        "header": header, "start_value": start, "end_value": end,
        "change": float(end - start),
        "header_references": [f"Metrics!{column}1"],
        "start_reference": f"Metrics!{column}2",
        "end_reference": f"Metrics!{column}4",
    }
