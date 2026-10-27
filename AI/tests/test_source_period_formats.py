"""Only unambiguous year-first strings extend the shared period parser."""
from datetime import datetime

import pytest

from app.agent.query.metric_observation_periods import source_period, source_period_grain
from app.agent.query.metric_observation_render import _period_label
from app.agent.query.metric_observations import horizontal_observations
from app.agent.query.metric_record_observations import dated_record_observations
from app.agent.query.trend_answers import trend_answer
from app.agent.query.trend_sources import trend_candidates
from tests.support.large_workbook_fixtures import offline
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("text,expected,grain", [
    ("2024-01", datetime(2024, 1, 1), "month"),
    ("2024/01", datetime(2024, 1, 1), "month"),
    (" 2024.1 ", datetime(2024, 1, 1), "month"),
    ("2024/01/31", datetime(2024, 1, 31), None),
    ("2024.01.31", datetime(2024, 1, 31), None),
    ("2024-02-29", datetime(2024, 2, 29), None),
    ("2024/2/29", datetime(2024, 2, 29), None),
    ("2024-01-31T12:30:00", datetime(2024, 1, 31, 12, 30), None),
    ("2024", datetime(2024, 1, 1), None),
    ("FY2024E", datetime(2024, 1, 1), None),
    ("Jan 2024", datetime(2024, 1, 1), "month"),
    ("2024 Nov", datetime(2024, 11, 1), "month"),
    (" 2024 SEPTEMBER ", datetime(2024, 9, 1), "month"),
    ("Feb.-2024", datetime(2024, 2, 1), "month"),
])
def test_year_first_formats_keep_valid_dates_and_month_grain(text, expected, grain):
    assert source_period(text) == expected
    assert source_period_grain(text) == grain


@pytest.mark.parametrize("text", [
    "01/02/2024", "31/01/2024", "01.02.2024", "24/01/31", "2024/01-31",
    "2024-13", "2024/00", "2024.02.30", "2023/02/29", "2024/01/00", "2024-01-32",
    "0000/01/01", "2024/01/31 extra", "Jan 24", "2024 November estimate", "2024 Smarch",
    "2024/1/2/3", True, float("nan"), float("inf"),
])
def test_invalid_or_ambiguous_dates_are_not_guessed(text):
    assert source_period(text) is None
    assert source_period_grain(text) is None


@pytest.mark.parametrize("horizontal", [False, True])
@pytest.mark.parametrize("separator", ["-", "/", "."])
def test_month_only_trends_do_not_invent_day_one(horizontal, separator):
    dates = [f"2024{separator}01", f"2024{separator}02", f"2024{separator}03"]
    matrix = ([["Metric", *dates], ["Total Employees", 100, 80, 90]] if horizontal else
              [["Date", "Total Employees"], *[[date, value] for date, value in zip(dates, [100, 80, 90])]])
    summary, index = table_fixture([(1, 1, matrix)])
    candidates = trend_candidates(summary, index, "전체 직원 수의 월별 추이를 설명해줘")
    assert len(candidates) == 1 and not candidates[0].error
    assert {point.grain for point in candidates[0].observations} == {"month"}
    answer = trend_answer("전체 직원 수의 월별 추이를 설명해줘", summary, index)
    assert answer.verification.level == "request_checked"
    assert "2024년 1월" in answer.answer and "반등" in answer.answer
    assert "2024-01-01" not in answer.answer


def test_month_only_and_exact_day_are_not_the_same_series_grain():
    summary, index = table_fixture([(1, 1, [["Date", "Total Employees"],
        ["2024-01", 100], ["2024-02-01", 120]])])
    answer = trend_answer("전체 직원 수의 추이를 설명해줘", summary, index)
    assert answer.verification.level != "request_checked"


@pytest.mark.parametrize("horizontal", [False, True])
def test_existing_observation_paths_keep_month_grain_and_label(horizontal):
    matrix = ([["Metric", "2024-01", "2024-02"], ["Revenue", 10, 20]] if horizontal else
              [["Company", "Date", "Revenue"], ["Alpha Systems", "2024-01", 10],
               ["Alpha Systems", "2024-02", 20]])
    _, index = table_fixture([(1, 1, matrix)])
    extractor = horizontal_observations if horizontal else dated_record_observations
    points = extractor(list(index.rows), "Alpha Systems Revenue")
    assert len(points) == 2 and all(point.grain == "month" for point in points)
    assert _period_label(points[0]) == "2024년 1월 월간"
