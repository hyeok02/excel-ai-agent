"""Calendar aggregation has independent original-cell arithmetic oracles."""
from datetime import date, timedelta
import pytest

from app.agent.query.resampled_trend_answers import resampled_trend_answer
from tests.support.large_workbook_fixtures import offline
from tests.support.trend_scoped_fixtures import normalize_formulas
from tests.tabular_query_fixtures import table_fixture


def daily(start=date(2024, 1, 1), days=60, metric="매출 (KRW)", values=None):
    return [["Date", metric], *[[(start + timedelta(days=n)).isoformat(),
                                 values[n] if values else 10] for n in range(days)]]


def answer(matrix, question="일별 매출 (KRW)을 월별 합계로 보여줘"):
    summary, index = table_fixture([(1, 1, matrix)])
    normalize_formulas(summary)
    return resampled_trend_answer(question, summary, index)


def checked(result):
    assert result is not None
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked", result.model_dump()


def unsafe(result):
    assert result is not None
    assert result.status != "answered", result.model_dump()
    assert result.verification.level != "request_checked", result.model_dump()


def test_daily_to_monthly_without_trend_word_uses_all_days_and_original_cells():
    matrix = daily()
    result = answer([matrix[0], *matrix[:0:-1]])
    checked(result)
    assert "2024년 1월: 310원" in result.answer and "2024년 2월: 290원" in result.answer
    assert {f"B{row}" for row in range(2, 62)} <= {cell.reference for cell in result.evidence}
    assert all(cell.value in {"Date", "매출 (KRW)", 10} or str(cell.value).startswith("2024-")
               for cell in result.evidence)


@pytest.mark.parametrize("statistic, expected", [("평균", "15원"), ("최솟값", "0원"), ("최댓값", "30원")])
def test_explicit_operators_and_single_bucket(statistic, expected):
    result = answer(daily(days=31, values=list(range(31))), f"매출 (KRW) 월별 {statistic} 보여줘")
    checked(result)
    assert f"2024년 1월: {expected}" in result.answer


def test_daily_quarterly_sum_uses_all_91_days_in_leap_year():
    result = answer(daily(days=91), "매출 (KRW) 분기별 합계 보여줘")
    checked(result)
    assert "2024년 1분기: 910원" in result.answer


def test_monthly_amounts_can_be_summed_into_quarters():
    matrix = [["Date", "매출 (KRW)"], *[[f"2024-{n:02}", n] for n in range(1, 7)]]
    result = answer(matrix, "매출 (KRW) 분기별 합계 추이를 보여줘")
    checked(result)
    assert "2024년 1분기: 6원" in result.answer and "2024년 2분기: 15원" in result.answer


def test_monthly_amounts_can_be_summed_into_years():
    matrix = [["Date", "매출 (KRW)"], *[[f"2024-{n:02}", n] for n in range(1, 13)]]
    result = answer(matrix, "매출 (KRW) 연도별 합계 보여줘")
    checked(result)
    assert "2024년: 78원" in result.answer


def test_end_observed_stock_is_not_summed_and_original_dates_are_shown():
    result = answer(daily(metric="인원", values=list(range(60))), "인원 월별 마지막 관측값 추이를 보여줘")
    checked(result)
    assert "2024년 1월: 30명" in result.answer and "2024년 2월: 59명" in result.answer
    assert "2024-01-31" in result.answer and "2024-02-29" in result.answer


def test_grouped_filtered_resampling_does_not_include_other_population():
    base = daily()
    matrix = [["Date", "매출 (KRW)", "부서", "사업장"],
              *[[row[0], row[1] * scale, group, "서울"] for group, scale in [("서비스", 1), ("개발", 2)]
                for row in base[1:]], ["2024-01-01", 9999, "서비스", "부산"]]
    result = answer(matrix, "서울 사업장만 부서별 매출 (KRW) 월별 합계 추이를 비교해줘")
    checked(result)
    assert "310원" in result.answer and "620원" in result.answer and "9,999" not in result.answer


def test_incomplete_calendar_discloses_partial_aggregation_without_green_badge():
    result = answer(daily(days=40))
    unsafe(result)
    assert result.status == "limited" and "2024년 2월: 90원" in result.answer
    assert any("전체 기간 집계로 확정하지" in limitation for limitation in result.limitations)


def test_last_observed_date_not_calendar_end_is_clearly_limited():
    result = answer(daily(days=40, metric="인원"), "인원 월별 기말값 보여줘")
    unsafe(result)
    assert "2024-02-09" in result.answer
    assert any("기말값으로 확정하지" in limitation for limitation in result.limitations)


def test_unknown_aggregation_is_not_replaced_and_unrequested_aggregation_is_not_invented():
    unsafe(answer(daily(), "매출 (KRW) 월별 중앙값 보여줘"))
    assert answer(daily(), "매출 (KRW) 월별 추이 보여줘") is None


def test_single_original_observation_can_be_shown_as_partial_bucket_not_blocked():
    result = answer(daily(days=1))
    unsafe(result)
    assert result.status == "limited" and "2024년 1월: 10원" in result.answer


def test_single_exact_period_end_observation_is_enough_for_last_value():
    result = answer(daily(start=date(2024, 1, 31), days=1, metric="인원"), "인원 월별 마지막 관측값 보여줘")
    checked(result)
    assert "2024년 1월: 10명" in result.answer
    assert "반등" not in result.answer and "상승" not in result.answer


def test_single_observation_never_becomes_an_unqualified_regular_trend():
    from app.agent.query.trend_answers import trend_answer
    summary, index = table_fixture([(1, 1, daily(days=1, metric="인원"))])
    result = trend_answer("인원 평균 추이를 보여줘", summary, index)
    unsafe(result)
