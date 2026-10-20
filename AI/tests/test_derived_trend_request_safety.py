"""Derived syntax must not consume source names or silently ignore conditions."""
import pytest

from app.agent.query.derived_trend_answers import derived_trend_answer
from tests.support.large_workbook_fixtures import offline
from tests.support.trend_scoped_fixtures import formats, refused
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("label", ["Revenue Growth Rate", "Market Share", "증감률", "비중"])
def test_existing_rate_column_keeps_original_trend_path(label):
    summary, index = table_fixture([(1, 1, [["Date", label], ["2024-01-31", 0.1],
                                         ["2024-02-29", 0.2], ["2024-03-31", 0.15]])])
    assert derived_trend_answer(f"{label} 추이를 설명해줘", summary, index) is None


@pytest.mark.parametrize("question", ["Total Employees 추이를 설명해줘", "이 파일을 요약해줘",
                                      "Total Employees는 몇 명이야?", "Total Employees의 증가율은 얼마야?"])
def test_unrelated_questions_are_not_hijacked(question):
    summary, index = table_fixture([(1, 1, [["Date", "Total Employees"], ["2023", 100], ["2024", 120]])])
    assert derived_trend_answer(question, summary, index) is None


@pytest.mark.parametrize("extra", ["서울만", "평균도", "세금 제외", "USD로 환산", "또는 Revenue", "상위 3개"])
def test_growth_never_disregards_filters_aggregates_conversions_or_alternatives(extra):
    summary, index = table_fixture([(1, 1, [["Date", "Total Employees"], ["2022", 100], ["2023", 120], ["2024", 150]])])
    refused(derived_trend_answer(f"Total Employees 증감률 추이를 설명해줘 {extra}", summary, index))


def test_unknown_amount_unit_is_limited_instead_of_verified():
    summary, index = table_fixture([(1, 1, [["Date", "Revenue"], ["2022", 100], ["2023", 120], ["2024", 150]])])
    answer = derived_trend_answer("Revenue 증감률 추이를 설명해줘", summary, index)
    assert answer.status == "limited" and answer.verification.level == "source_checked"


def test_two_growth_bases_cannot_be_merged_or_ignored():
    summary, index = table_fixture([(1, 1, [["Date", "Total Employees"], ["2022", 100], ["2023", 120], ["2024", 150]])])
    refused(derived_trend_answer("Total Employees 전년 동기 대비 전월 대비 증감률 추이를 설명해줘", summary, index))


def test_source_label_with_year_keeps_year_literal_not_date_filter():
    summary, index = table_fixture([(1, 1, [["Date", "Team 2024 Employees"], ["2022", 100], ["2023", 120], ["2024", 150]])])
    answer = derived_trend_answer("Team 2024 Employees 증감률 추이를 설명해줘", summary, index)
    assert answer.status == "answered", answer.model_dump()
    assert "2개 시점" in answer.answer and "2023년: 20%" in answer.answer


def test_quick_percent_change_english_is_not_confused_with_share():
    summary, index = table_fixture([(1, 1, [["Date", "Total Employees"], ["2022", 100], ["2023", 120], ["2024", 150]])])
    answer = derived_trend_answer("Total Employees percent change trend", summary, index)
    assert answer.status == "answered", answer.model_dump()


def test_existing_percent_metric_needs_an_explicit_additional_growth_operation():
    summary, index = table_fixture([(1, 1, [["Date", "Revenue Growth Rate"], ["2022", 0.2], ["2023", 0.4], ["2024", 0.3]])])
    index = formats(summary, index, {"B2": "0.00%", "B3": "0.00%", "B4": "0.00%"})
    assert derived_trend_answer("Revenue Growth Rate 추이", summary, index) is None
    answer = derived_trend_answer("Revenue Growth Rate의 증감률 추이", summary, index)
    assert answer.status == "answered", answer.model_dump()
    assert "100% → -25%" in answer.answer
    assert {0.2, 0.4, 0.3} <= {item.value for item in answer.evidence}
