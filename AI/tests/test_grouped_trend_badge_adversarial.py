"""Competing scope and pre-aggregation context must not vanish behind a badge."""
import pytest

from app.agent.query.trend_answers import trend_answer
from tests.support.large_workbook_fixtures import offline
from tests.tabular_query_fixtures import table_fixture
from tests.test_grouped_trend_adversarial import QUESTION, answer, checked, grouped, unsafe


def test_competing_ambiguous_date_axis_cannot_disappear_during_grouped_routing():
    alternative = grouped()
    alternative[0].append("Effective Date")
    for row in alternative[1:]:
        row.append(row[0])
    summary, index = table_fixture([(1, 1, grouped()), (12, 1, alternative)])
    unsafe(trend_answer(QUESTION, summary, index))
    checked(trend_answer("'Arbitrary'!A1:D7 범위에서 " + QUESTION, summary, index))


@pytest.mark.parametrize("statistic", ["합계", "평균", "최솟값", "최댓값"])
def test_aggregation_cannot_erase_mixed_original_month_and_day_grains(statistic):
    matrix = [["Date", "부서", "인원", "사업장"],
              ["2024-01", "서비스", 100, "서울"], ["2024-01-01", "서비스", 20, "서울"],
              ["2024-02", "서비스", 130, "서울"], ["2024-02-01", "서비스", 40, "서울"]]
    unsafe(answer(matrix, f"서울 사업장만 부서별 인원 {statistic} 추이를 비교해줘"))


def test_subtotal_and_detail_rows_with_explicit_role_cannot_be_blindly_summed():
    matrix = [["Date", "부서", "인원", "사업장", "Row Role"],
              ["2024-01-31", "서비스", 100, "서울", "Subtotal"],
              ["2024-01-31", "서비스", 40, "서울", "Detail"],
              ["2024-01-31", "서비스", 60, "서울", "Detail"],
              ["2024-02-29", "서비스", 120, "서울", "Subtotal"],
              ["2024-02-29", "서비스", 70, "서울", "Detail"],
              ["2024-02-29", "서비스", 50, "서울", "Detail"]]
    unsafe(answer(matrix, "서울 사업장만 부서별 인원 합계 추이를 비교해줘"))


@pytest.mark.parametrize("predicate", ["인원 100 이상하지 않은", "사업장 does not contain 서울"])
def test_partial_predicate_recognition_does_not_erase_unknown_negation(predicate):
    unsafe(answer(grouped(), f"{predicate} 부서별 인원 추이를 비교해줘"))


@pytest.mark.parametrize("dates", [
    ["2024A", "2024E", "2025A", "2025E"], ["2024A", "2025E"],
    ["FY2024A", "FY2024E", "FY2025A", "FY2025E"],
])
def test_original_year_actual_estimate_suffixes_cannot_be_discarded(dates):
    matrix = [["Date", "부서", "인원", "사업장"],
              *[[date, "서비스", 100 + index * 20, "서울"] for index, date in enumerate(dates)]]
    unsafe(answer(matrix, "서울 사업장만 부서별 인원 합계 추이를 비교해줘"))


@pytest.mark.parametrize("field, first, second, forbidden", [
    ("Currency", "USD", "EUR", "200미국 달러"),
    ("Magnitude", "million", "thousand", "200백만"),
])
def test_row_unit_control_is_not_borrowed_from_the_first_group(field, first, second, forbidden):
    matrix = [["Date", field, "Revenue"],
              ["2024-01-01", first, 100], ["2024-02-01", first, 110],
              ["2024-01-01", second, 200], ["2024-02-01", second, 220]]
    result = answer(matrix, f"{field}별 Revenue 추이를 비교해줘")
    unsafe(result)
    assert forbidden not in result.answer


def test_filtered_row_currency_cannot_borrow_an_excluded_population_control():
    matrix = [["Date", "Currency", "Revenue"],
              ["2024-01-01", "USD", 100], ["2024-02-01", "USD", 110],
              ["2024-01-01", "EUR", 200], ["2024-02-01", "EUR", 220]]
    result = answer(matrix, "EUR Currency만 Revenue 추이를 설명해줘")
    assert "200미국 달러" not in result.answer
    if result.status == "answered":
        assert "200유로 → 220유로" in result.answer
        assert ("B4", "EUR") in {(cell.reference, cell.value) for cell in result.evidence}
    else:
        unsafe(result)


def test_explicit_unit_caption_and_row_control_conflict_cannot_be_certified():
    matrix = [["Date", "Currency", "Revenue (USD)"],
              ["2024-01-01", "EUR", 200], ["2024-02-01", "EUR", 220]]
    unsafe(answer(matrix, "EUR Currency만 Revenue (USD) 추이를 설명해줘"))


def test_explicit_row_magnitude_cannot_be_ignored_by_people_count_shortcut():
    matrix = [["Date", "Magnitude", "Employees"],
              ["2024-01-01", "million", 1], ["2024-02-01", "million", 2],
              ["2024-01-01", "thousand", 3], ["2024-02-01", "thousand", 4]]
    result = answer(matrix, "Magnitude별 Employees 추이를 비교해줘")
    unsafe(result)
    assert "1명 → 2명" not in result.answer


@pytest.mark.parametrize("field, value", [("Currency", "USD / EUR"), ("Magnitude", "million / thousand")])
def test_one_row_control_with_conflicting_unit_mentions_is_not_first_match_wins(field, value):
    matrix = [["Date", field, "Revenue"],
              ["2024-01-01", value, 100], ["2024-02-01", value, 110]]
    unsafe(answer(matrix, f"{field}별 Revenue 추이를 비교해줘"))
