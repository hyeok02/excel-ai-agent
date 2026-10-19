"""Date bounds must not consume source names or truncate the final day."""
import pytest

from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import QUESTION, checked, direct
from tests.tabular_query_fixtures import table_fixture

DATES = ["2023-12-31", "2024-03-31", "2024-06-30", "2025-03-31"]


def _company_source(entity, sheet="Arbitrary"):
    matrix = [["Date", "Total Employees", "Company"],
              *[[date, value, entity] for date, value in zip(DATES, [50, 100, 120, 10])]]
    return table_fixture([(1, 1, matrix)], sheet_name=sheet)


@pytest.mark.parametrize("entity", ["Project2024", "Project 2024", "Studio 2024"])
def test_year_inside_bound_entity_name_does_not_filter_the_entire_trajectory(entity):
    summary, index = _company_source(entity)
    answer = direct(summary, index, f"{entity} {QUESTION}")
    checked(answer)
    assert "2023-12-31" in answer.answer and "2025-03-31" in answer.answer
    assert "4개 관측값" in answer.answer
    assert "50명 → 10명" in answer.answer


@pytest.mark.parametrize("entity", ["Project2024", "Project 2024", "Studio 2024"])
def test_separate_explicit_year_survives_consuming_the_entity_name(entity):
    summary, index = _company_source(entity)
    answer = direct(summary, index, f"{entity} 2024년 {QUESTION}")
    checked(answer)
    assert "2024-03-31" in answer.answer and "2024-06-30" in answer.answer
    assert "2023-12-31" not in answer.answer and "2025-03-31" not in answer.answer
    assert "2개 관측값" in answer.answer
    assert "100명 → 120명" in answer.answer


@pytest.mark.parametrize("period", [
    "2024년", "2024년 3월 31일부터 2024년 12월 31일까지",
    "2024년 3월부터 2024년 12월까지",
])
def test_calendar_end_date_includes_source_timestamps_later_on_that_day(period):
    dates = ["2024-03-31T12:00:00", "2024-06-30T12:00:00",
             "2024-09-30T12:00:00", "2024-12-31T23:59:59.999999"]
    matrix = [["Date", "Total Employees"],
              *[[date, value] for date, value in zip(dates, [100, 150, 200, 20])]]
    summary, index = table_fixture([(1, 1, matrix)])
    answer = direct(summary, index, f"{period} {QUESTION}")
    checked(answer)
    assert "2024-12-31 23:59:59.999999" in answer.answer
    assert "4개 관측값" in answer.answer and "100명 → 20명" in answer.answer
    assert "80명 감소" in answer.answer


@pytest.mark.parametrize("entity,sheet", [("2024", "Arbitrary"), ("Example Co", "2024")])
def test_numeric_source_name_cannot_erase_an_explicit_calendar_year(entity, sheet):
    summary, index = _company_source(entity, sheet)
    answer = direct(summary, index, f"2024년 {QUESTION}")
    if answer is not None and answer.verification.level == "request_checked":
        assert "2023-12-31" not in answer.answer and "2025-03-31" not in answer.answer
        assert "2개 관측값" in answer.answer


def test_bare_numeric_name_or_year_cannot_certify_an_unbounded_history():
    summary, index = _company_source("2024", "2024")
    answer = direct(summary, index, f"2024 {QUESTION}")
    if answer is not None and answer.verification.level == "request_checked":
        assert "2023-12-31" not in answer.answer and "2025-03-31" not in answer.answer
