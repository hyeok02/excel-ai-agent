"""Calendar subperiods bind exact inclusive bounds without workbook exceptions."""
from dataclasses import replace
from datetime import datetime

import pytest

from app.agent.query.trend_date_bounds import parse_trend_date_bounds
from tests.support.trend_fixtures import observations


def source():
    return observations([10, 12, 9, 15], dates=[
        "2023-12-31", "2024-03-31", "2024-06-30", "2024-12-31"])


@pytest.mark.parametrize("phrase,start,end", [
    ("2024년 2분기", "2024-04-01", "2024-06-30"),
    ("2024년 제 2분기", "2024-04-01", "2024-06-30"),
    ("2024년도 2분기", "2024-04-01", "2024-06-30"),
    ("Q1 2024", "2024-01-01", "2024-03-31"),
    ("2024 Q4", "2024-10-01", "2024-12-31"),
    ("2024-Q4", "2024-10-01", "2024-12-31"),
    ("2nd quarter 2024", "2024-04-01", "2024-06-30"),
    ("third quarter of 2024", "2024-07-01", "2024-09-30"),
    ("quarter 4 2024", "2024-10-01", "2024-12-31"),
    ("2024년 상반기", "2024-01-01", "2024-06-30"),
    ("2024년 하반기", "2024-07-01", "2024-12-31"),
    ("H1 2024", "2024-01-01", "2024-06-30"),
    ("2024H2", "2024-07-01", "2024-12-31"),
    ("1H 2024", "2024-01-01", "2024-06-30"),
    ("second half of 2024", "2024-07-01", "2024-12-31"),
    ("first half-year 2024", "2024-01-01", "2024-06-30"),
    ("2023년 4분기부터 2024년 2분기까지", "2023-10-01", "2024-06-30"),
    ("2024년 1분기부터 2분기까지", "2024-01-01", "2024-06-30"),
    ("2024년 1분기에서 2분기까지", "2024-01-01", "2024-06-30"),
    ("Q1 to Q2 2024", "2024-01-01", "2024-06-30"),
    ("between Q1 and Q2 2024", "2024-01-01", "2024-06-30"),
    ("from Q4 2023 to Q2 2024", "2023-10-01", "2024-06-30"),
    ("2024 Q1 to Q2 2025", "2024-01-01", "2025-06-30"),
    ("2023년 하반기부터 2024년 상반기까지", "2023-07-01", "2024-06-30"),
    ("2024년 2분기 이후", "2024-04-01", None),
    ("2024년 상반기 이전", None, "2024-06-30"),
    ("after Q2 2024", "2024-07-01", None),
    ("before H1 2024", None, "2023-12-31"),
])
def test_calendar_period_bounds(phrase, start, end):
    bounds, error = parse_trend_date_bounds(f"Metric trend {phrase}", source())
    assert error is None, error
    assert bounds.start == (datetime.fromisoformat(start) if start else None)
    assert bounds.end == (datetime.fromisoformat(end) if end else None)
    assert "달력 분기·반기 기준" in bounds.note
    assert "경계 포함" in bounds.note


@pytest.mark.parametrize("phrase", [
    "Q1", "상반기", "second half", "2024년 5분기", "Q0 2024", "2024 H3",
    "2024년 3반기", "2024 Q1 or 2024 Q3", "Q1 and Q3 2024", "2024 Q1 2024 Q2",
    "2024 Q3 to Q1", "2024 Q1 2025", "2024 Q1 to 2025 Q2 to 2026 Q3",
    "FY2024 Q1", "fiscal 2024 H1", "2024 회계연도 상반기",
    "2024 Q1 최근 1년", "2024 Q1 June", "after Q1 2024 이전",
    "2024 Q1 2024-06-30", "2024 Q1 to 2025-02", "2024 Q1 또는 상반기",
])
def test_ambiguous_calendar_periods_do_not_drop_constraints(phrase):
    bounds, error = parse_trend_date_bounds(f"Metric trend {phrase}", source())
    assert bounds is None and error


@pytest.mark.parametrize("label", ["Q1 Employees", "H1 Revenue", "상반기 매출", "First Half Employees"])
def test_period_words_inside_bound_metric_names_are_not_filters(label):
    items = [replace(item, label=replace(item.label, value=label)) for item in source()]
    bounds, error = parse_trend_date_bounds(f"{label} trend", items)
    assert error is None and bounds.start is None and bounds.end is None
    scoped, error = parse_trend_date_bounds(f"{label} trend 2024년 2분기", items)
    assert error is None and scoped.start == datetime(2024, 4, 1)


def test_fiscal_year_labels_do_not_define_quarter_start_months():
    items = [replace(item, period_cell=replace(item.period_cell, value=f"FY{item.period.year}"))
             for item in source()]
    bounds, error = parse_trend_date_bounds("Metric FY2024 Q2 trend", items)
    assert bounds is None and "회계" in error
