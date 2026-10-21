"""Adversarial period aggregation must not mint an unwarranted verified badge."""
from dataclasses import replace
from datetime import date
import pytest

from app.agent.query.resampled_trend_answers import resampled_trend_answer
from tests.support.large_workbook_fixtures import offline
from tests.support.trend_scoped_fixtures import formats
from tests.tabular_query_fixtures import table_fixture
from tests.test_resampled_trend_answers import answer, daily, unsafe


@pytest.mark.parametrize("value", [None, "=EXTERNAL_PROVIDER()", "unknown"])
def test_invalid_period_value_is_not_skipped_or_filled(value):
    matrix = daily()
    matrix[20][1] = value
    unsafe(answer(matrix))


@pytest.mark.parametrize("duplicate", [10, 999])
def test_duplicate_original_date_never_counts_twice_even_if_identical(duplicate):
    matrix = daily()
    matrix.append(["2024-01-10", duplicate])
    result = answer(matrix)
    unsafe(result)
    assert "같은 그룹·날짜" in result.answer


@pytest.mark.parametrize("metric", ["인원", "재고", "잔액 (KRW)", "Debt (USD)", "Growth Rate", "EPS (USD)",
                                    "Staff Count", "Employee Count", "Number of Staff", "주가 (KRW)",
                                    "Price (USD)", "Cash (USD)", "ClosingPrice (USD)", "closing_price (USD)"])
def test_stock_and_nonadditive_measures_cannot_be_summed_over_time(metric):
    result = answer(daily(metric=metric), f"{metric} 월별 합계 보여줘")
    unsafe(result)
    assert "평균 또는 마지막 관측값" in result.answer


def test_percent_formatted_values_cannot_be_summed_over_time():
    summary, index = table_fixture([(1, 1, daily())])
    index = formats(summary, index, {f"B{row}": "0.00%" for row in range(2, 62)})
    unsafe(resampled_trend_answer("매출 (KRW) 월별 합계 보여줘", summary, index))


def test_explicit_people_number_format_cannot_be_summed_under_an_arbitrary_label():
    summary, index = table_fixture([(1, 1, daily(metric="Metric"))])
    index = formats(summary, index, {f"B{row}": '0"명"' for row in range(2, 62)})
    result = resampled_trend_answer("Metric 월별 합계 보여줘", summary, index)
    unsafe(result)
    assert "평균 또는 마지막 관측값" in result.answer


def test_mixed_formats_and_date_grains_are_not_aggregated():
    summary, index = table_fixture([(1, 1, daily())])
    index = formats(summary, index, {"B20": "0.00%"})
    unsafe(resampled_trend_answer("매출 (KRW) 월별 합계 보여줘", summary, index))
    matrix = daily()
    matrix[20][0] = "2024-01"
    unsafe(answer(matrix))


def test_monthly_source_cannot_be_presented_as_requested_daily_source():
    matrix = [["Date", "매출 (KRW)"], ["2024-01", 100], ["2024-02", 200], ["2024-03", 300]]
    result = answer(matrix, "일별 매출 (KRW) 분기별 합계 보여줘")
    unsafe(result)
    assert "일별 원본" in result.answer


def test_annual_source_cannot_be_split_into_months():
    matrix = [["Date", "매출 (KRW)"], ["2023", 100], ["2024", 200]]
    unsafe(answer(matrix))


@pytest.mark.parametrize("question", [
    "매출 (KRW) 월별 합계와 평균 보여줘",
    "매출 (KRW) 월별 합계와 분기별 합계 보여줘",
    "매출 (KRW) 월별 가중 평균 보여줘",
    "매출 (KRW) 회계 분기별 합계 보여줘",
    "서울만 매출 (KRW) 월별 합계 보여줘",
    "매출 (KRW) 월별 합계와 내년 예측 보여줘",
    "매출 (KRW) 월별 합계를 달러로 환산해줘",
    "매출 (KRW) 월별 합계를 인원으로 나눠줘",
])
def test_unbound_conditions_or_other_operations_are_not_dropped(question):
    unsafe(answer(daily(), question))


def test_missing_dates_hidden_rows_and_incomplete_source_are_not_verified():
    matrix = daily()
    matrix[10][0] = None
    unsafe(answer(matrix))
    summary, index = table_fixture([(1, 1, daily())])
    summary.sheets[0].regions[0].hidden_rows.append(20)
    unsafe(resampled_trend_answer("매출 (KRW) 월별 합계 보여줘", summary, index))
    summary, index = table_fixture([(1, 1, daily())])
    index = replace(index, rows=index.rows[:-1], truncated=True,
                    truncated_sheet_names=frozenset({"Arbitrary"}))
    unsafe(resampled_trend_answer("매출 (KRW) 월별 합계 보여줘", summary, index))


def test_sparse_daily_observations_cannot_claim_full_calendar_months():
    matrix = [["Date", "매출 (KRW)"], ["2024-01-01", 10], ["2024-01-31", 20],
              ["2024-02-01", 30], ["2024-02-29", 40]]
    result = answer(matrix)
    unsafe(result)
    assert "2024년 1월: 30원" in result.answer and "2024년 2월: 70원" in result.answer


def test_intraday_values_are_not_assumed_to_have_a_known_day_boundary():
    matrix = daily()
    matrix[1][0] = "2024-01-01T12:00:00"
    unsafe(answer(matrix))


def test_scenario_groups_do_not_claim_same_basis_comparison():
    matrix = [["Date", "매출 (KRW)", "Scenario"],
              *[[row[0], row[1], scenario] for scenario in ("Actual", "Forecast") for row in daily()[1:]]]
    result = answer(matrix, "Scenario별 매출 (KRW) 월별 합계 추이를 비교해줘")
    unsafe(result)
    assert any("실적/예상" in limitation for limitation in result.limitations)


def test_whole_missing_month_is_disclosed_and_not_green():
    matrix = [*daily(days=31), *daily(start=date(2024, 3, 1), days=31)[1:]]
    result = answer(matrix)
    unsafe(result)
    assert any("전혀 없는 기간" in limitation for limitation in result.limitations)


def test_requested_year_cannot_claim_all_months_when_only_jan_feb_exist():
    result = answer(daily(), "2024년 매출 (KRW) 월별 합계 보여줘")
    unsafe(result)
    assert any("전혀 없는 기간" in limitation for limitation in result.limitations)


@pytest.mark.parametrize("value", ["월별 합계", "Monthly Sum"])
def test_operation_words_inside_original_category_are_data(value):
    matrix = [["Date", "인원", "부서"], ["2024-01-31", 10, value], ["2024-02-29", 20, value]]
    assert answer(matrix, f"{value} 부서 인원 추이를 보여줘") is None
