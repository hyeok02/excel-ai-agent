"""Calendar windows are proven from dates before any value validation."""
from dataclasses import replace
from datetime import datetime

import pytest

from app.agent.query.trend_date_bounds import parse_trend_date_bounds, select_trend_periods
from app.agent.query.trend_request import trend_request_error
from tests.support.trend_fixtures import observations


def source():
    return observations([None, "=EXTERNAL()", "invalid", 130], dates=[
        "2023-06-30", "2024-06-01", "2024-06-30T23:59:59", "2025-06-30"])


@pytest.mark.parametrize("phrase,start,end", [
    ("2024년 6월 이후", "2024-06-01", None),
    ("2024년 6월 이전", None, "2024-06-30"),
    ("2024년 6월 15일 이후", "2024-06-15", None),
    ("2024년 6월 15일 이전", None, "2024-06-15"),
    ("after June 2024", "2024-07-01", None),
    ("before June 2024", None, "2024-05-31"),
    ("since June 2024", "2024-06-01", None),
    ("before 2024-06-15", None, "2024-06-14"),
    ("after 2024-06-15", "2024-06-16", None),
    ("2024년", "2024-01-01", "2024-12-31"),
    ("2024년 1월부터 3월까지", "2024-01-01", "2024-03-31"),
    ("from January to March 2024", "2024-01-01", "2024-03-31"),
    ("after 2024-06-01 before 2024-06-30", "2024-06-02", "2024-06-29"),
])
def test_absolute_bounds_and_inclusion_are_explicit(phrase, start, end):
    bounds, error = parse_trend_date_bounds(f"Metric 추이 {phrase}", source())
    assert error is None
    assert bounds.start == (datetime.fromisoformat(start) if start else None)
    assert bounds.end == (datetime.fromisoformat(end) if end else None)
    assert "경계 포함" in bounds.note
    assert not bounds.relative
    assert trend_request_error(f"Metric 추이 {phrase}", source(), ()) is None


@pytest.mark.parametrize("phrase,start", [
    ("최근 1년", "2024-06-30"), ("최근 6개월", "2024-12-30"),
    ("최근 1년간", "2024-06-30"), ("last 1 year", "2024-06-30"),
    ("recent 6 months", "2024-12-30"), ("past 6 months", "2024-12-30"),
    ("최근 1년 동안", "2024-06-30"), ("over the last 6 months", "2024-12-30"),
])
def test_relative_period_anchors_to_source_not_today(phrase, start):
    bounds, error = parse_trend_date_bounds(f"Metric 추이 {phrase}", source())
    assert error is None and bounds.relative
    assert bounds.start == datetime.fromisoformat(start)
    assert bounds.end == datetime(2025, 6, 30)
    assert "오늘이 아닌" in bounds.note and "2025-06-30 기준" in bounds.note
    assert "양끝 포함" in bounds.note
    assert trend_request_error(f"Metric 추이 {phrase}", source(), ()) is None


@pytest.mark.parametrize("phrase", [
    "최근", "최신", "오늘 기준 최근 1년", "최근 0개월", "최근 -1년", "최근 1.5년",
    "최근 10001개월", "최근 1년 6개월", "최근 1년 또는 최근 6개월",
    "2025년 기준 최근 1년", "2024년 13월 이후", "2024년 2월 30일 이후",
    "2025년부터 2024년까지", "2024년 이전부터", "이후", "2024년 2025년 2026년",
    "before 2024년 이후", "2024년 6월 이후 이전", "작년", "올해", "last year",
    "2024년 혹은 2025년", "2024년 3월과 2024년 9월", "2024년 1월부터 3월까지 2025년",
])
def test_ambiguous_or_invalid_time_scope_is_not_silently_dropped(phrase):
    bounds, error = parse_trend_date_bounds(f"Metric 추이 {phrase}", source())
    assert bounds is None and error


def test_selection_uses_dates_only_and_includes_end_day_times():
    items = source()
    bounds, error = parse_trend_date_bounds("Metric 추이 2024년 6월 이전", items)
    assert error is None
    assert select_trend_periods(items, bounds) == tuple(items[:3])


@pytest.mark.parametrize("latest,phrase,expected", [
    ("2024-02-29", "최근 1년", "2023-02-28"),
    ("2025-03-31", "최근 1개월", "2025-02-28"),
    ("2025-08-31", "최근 6개월", "2025-02-28"),
])
def test_relative_month_arithmetic_clamps_month_end(latest, phrase, expected):
    items = observations([None, None], dates=["2020-01-01", latest])
    bounds, error = parse_trend_date_bounds(f"Metric {phrase} 추이", items)
    assert error is None and bounds.start == datetime.fromisoformat(expected)


def test_source_name_with_relative_words_is_not_an_implicit_window():
    items = source()
    items = [replace(item, label=replace(item.label, value="Last 12 months Revenue")) for item in items]
    bounds, error = parse_trend_date_bounds("Last 12 months Revenue 추이", items)
    assert error is None and not bounds.relative
    assert bounds.start is None and bounds.end is None


def test_identifier_year_and_explicit_calendar_year_remain_independent():
    items = source()
    items = [replace(item, label=replace(item.label, value="Metric 2024")) for item in items]
    bounds, error = parse_trend_date_bounds("Metric 2024의 추이 2025년 이후", items)
    assert error is None and bounds.start == datetime(2025, 1, 1)


def test_all_selected_translated_metric_aliases_are_consumed():
    items = source()
    labels = [replace(item, label=replace(item.label, value="Total Employees")) for item in items]
    labels += [replace(item, label=replace(item.label, value="Services")) for item in items]
    assert trend_request_error("전체 직원 수와 서비스의 최근 1년 추이를 비교해줘", labels, ()) is None
