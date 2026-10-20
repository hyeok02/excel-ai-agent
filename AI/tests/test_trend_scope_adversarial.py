"""A trend badge needs a unique, complete date/metric population."""
from dataclasses import replace

import pytest

from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import direct, not_certified, source
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("middle", [None, "unknown", "=EXTERNAL_PROVIDER()", True])
def test_unknown_middle_metric_is_not_skipped_to_certify_endpoints(middle):
    summary, index = source([100, middle, 120, 130])
    not_certified(direct(summary, index))


@pytest.mark.parametrize("date", [None, "unknown", "=EXTERNAL_DATE()", "not a date"])
def test_unknown_middle_date_is_not_skipped(date):
    matrix = [["Date", "Total Employees"], ["2024-03-31", 100],
              [date, 200], ["2024-09-30", 110]]
    summary, index = table_fixture([(1, 1, matrix)])
    not_certified(direct(summary, index))


def test_conflicting_same_date_values_cannot_be_certified():
    matrix = [["Date", "Total Employees"], ["2024-03-31", 100],
              ["2024-06-30", 120], ["2024-06-30", 190], ["2024-09-30", 110]]
    summary, index = table_fixture([(1, 1, matrix)])
    not_certified(direct(summary, index))


def test_different_entities_are_not_one_chronological_population():
    matrix = [["Date", "Total Employees", "Company"], ["2024-03-31", 100, "North"],
              ["2024-06-30", 120, "North"], ["2024-09-30", 190, "South"]]
    summary, index = table_fixture([(1, 1, matrix)])
    not_certified(direct(summary, index))


def test_two_candidate_date_axes_cannot_be_arbitrarily_selected():
    matrix = [["Date", "Total Employees", "Effective Date"],
              ["2024-03-31", 100, "2023-03-31"],
              ["2024-06-30", 120, "2023-06-30"],
              ["2024-09-30", 110, "2023-09-30"]]
    summary, index = table_fixture([(1, 1, matrix)])
    not_certified(direct(summary, index))


@pytest.mark.parametrize("dimension, values", [
    ("Scenario", ["Actual", "Actual", "Forecast"]),
    ("Currency", ["USD", "USD", "EUR"]),
    ("Unit", ["명", "명", "%"]),
])
def test_changed_series_context_must_not_be_silently_mixed(dimension, values):
    matrix = [["Date", "Total Employees", dimension],
              ["2024-03-31", 100, values[0]], ["2024-06-30", 120, values[1]],
              ["2024-09-30", 110, values[2]]]
    summary, index = table_fixture([(1, 1, matrix)])
    not_certified(direct(summary, index))


def test_partial_index_without_original_provider_cannot_certify_full_history():
    summary, index = source()
    index = replace(index, rows=index.rows[:-1], truncated=True,
                    truncated_sheet_names=frozenset({"Arbitrary"}))
    not_certified(direct(summary, index))


@pytest.mark.parametrize("question", [
    "전체 직원 수가 120 이상인 기간만 추이를 설명해줘",
    "서울의 전체 직원 수의 기간별 추이를 설명해줘",
    "없는부서 직원 수의 기간별 추이를 설명해줘",
    "전체 직원 수와 Revenue의 기간별 추이를 설명해줘",
    "전체 직원 수의 기간별 추이와 내년 예상 인원을 설명해줘",
])
def test_extra_user_scope_cannot_be_ignored(question):
    summary, index = source()
    answer = direct(summary, index, question)
    # If a future implementation supports the extra scope, these cases should
    # be replaced with an independent calculation oracle, never a loose badge.
    not_certified(answer)


def test_inclusive_since_window_has_its_own_calculation_oracle():
    summary, index = source()
    answer = direct(summary, index, "2024년 6월 이후 전체 직원 수의 기간별 추이를 설명해줘")
    assert answer.verification.level == "request_checked"
    assert "150명 → 130명, 20명 감소(-13.33%)" in answer.answer
    assert "3개 관측값" in answer.answer
    assert "2024-03-31" not in answer.answer
    assert "2024-06-01" in answer.answer and "경계 포함" in answer.answer


@pytest.mark.parametrize("modifier", ["증가율", "감소율", "growth rate"])
def test_derived_metric_request_certifies_independent_calculation_not_raw_trajectory(modifier):
    summary, index = source()
    answer = direct(summary, index, f"전체 직원 수의 {modifier} 추이를 설명해줘")
    assert answer.status == "answered" and answer.verification.level == "request_checked"
    decrease = modifier == "감소율"
    expected = ["-50%", "20%", "-8.33%"] if decrease else ["50%", "-20%", "8.33%"]
    for date, value in zip(["2024-06-30", "2024-09-30", "2024-12-31"], expected):
        assert f"{date}: {value}" in answer.answer
    formula = "이전 기준값 - 현재값" if decrease else "현재값 - 이전 기준값"
    assert f"({formula}) / 이전 기준값 × 100" in answer.answer
    assert "3개 시점" in answer.answer and "100명 → 130명" not in answer.answer
    assert {("B2", 100), ("B3", 150), ("B4", 120), ("B5", 130)} <= {
        (cell.reference, cell.value) for cell in answer.evidence}


@pytest.mark.parametrize("modifier", ["비율", "percentage"])
def test_undefined_ratio_still_cannot_certify_raw_trajectory(modifier):
    summary, index = source()
    not_certified(direct(summary, index, f"전체 직원 수의 {modifier} 추이를 설명해줘"))


def test_incomplete_competing_population_cannot_disappear_during_selection():
    complete = [["Date", "Total Employees"], ["2024-03-31", 100],
                ["2024-06-30", 120], ["2024-09-30", 110]]
    incomplete = [["Date", "Total Employees"], ["2024-03-31", 800],
                  ["2024-06-30", None], ["2024-09-30", 700]]
    summary, index = table_fixture([(1, 1, complete), (7, 1, incomplete)])
    not_certified(direct(summary, index))


def test_yearly_request_cannot_certify_a_quarterly_path_within_one_year():
    summary, index = source()
    not_certified(direct(summary, index, "전체 직원 수의 연도별 추이를 설명해줘"))


def test_ambiguous_competing_date_axis_is_not_proof_of_an_irrelevant_helper():
    complete = [["Date", "Total Employees"], ["2024-03-31", 100],
                ["2024-06-30", 120], ["2024-09-30", 110]]
    competing = [["Date", "Total Employees", "Effective Date"],
                 ["2024-03-31", 800, "2023-03-31"],
                 ["2024-06-30", 900, "2023-06-30"],
                 ["2024-09-30", 700, "2023-09-30"]]
    summary, index = table_fixture([(1, 1, complete), (7, 1, competing)])
    not_certified(direct(summary, index))
