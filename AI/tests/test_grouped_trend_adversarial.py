"""Independent original-cell oracles for conditional and grouped trajectories."""
from dataclasses import replace

import pytest

from app.agent.query.trend_answers import trend_answer
from tests.support.large_workbook_fixtures import offline
from tests.support.trend_scoped_fixtures import formats, normalize_formulas
from tests.tabular_query_fixtures import table_fixture

QUESTION = "서울 사업장만 부서별 인원 추이를 비교해줘"
DATES = ["2024-01-31", "2024-02-29", "2024-03-31"]


def grouped(*, extra=(), scale=1):
    rows = [[date, group, count * scale, "서울"]
            for group, counts in [("서비스", [100, 80, 90]), ("개발", [40, 100, 50])]
            for date, count in zip(DATES, counts)]
    return [["Date", "부서", "인원", "사업장"], *rows[::-1], *extra]


def answer(matrix, question=QUESTION):
    summary, index = table_fixture([(1, 1, matrix)])
    normalize_formulas(summary)
    return trend_answer(question, summary, index)


def checked(result):
    assert result is not None
    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked", result.model_dump()


def unsafe(result):
    assert result is not None, "A conditional trend must not fall through to a model"
    assert result.verification.level != "request_checked", result.model_dump()
    assert result.status != "answered", result.model_dump()


def test_filter_and_all_group_paths_are_computed_in_chronological_order():
    result = answer(grouped(extra=[[DATES[1], "서비스", 9999, "부산"]]))
    checked(result)
    assert "서비스" in result.answer and "개발" in result.answer
    assert "100명 → 90명" in result.answer and "40명 → 50명" in result.answer
    assert "반등" in result.answer and "하락 전환" in result.answer
    assert result.answer.count("3개 관측값") == 2 and "9,999" not in result.answer
    references = {(cell.reference, cell.value) for cell in result.evidence}
    assert {(f"C{number}", grouped()[number - 1][2]) for number in range(2, 8)} <= references


@pytest.mark.parametrize("outside", [None, "=EXTERNAL_PROVIDER()", "unknown"])
def test_invalid_metric_in_explicitly_excluded_population_does_not_block(outside):
    checked(answer(grouped(extra=[[DATES[1], "서비스", outside, "부산"]])))


@pytest.mark.parametrize("statistic, expected", [("합계", "120명 → 170명"), ("평균", "60명 → 85명")])
def test_explicit_aggregate_has_independent_value_and_lineage_oracle(statistic, expected):
    matrix = [["Date", "부서", "인원", "사업장"],
              [DATES[0], "서비스", 100, "서울"], [DATES[0], "서비스", 20, "서울"],
              [DATES[1], "서비스", 130, "서울"], [DATES[1], "서비스", 40, "서울"]]
    result = answer(matrix, f"서울 사업장만 부서별 인원 {statistic} 추이를 비교해줘")
    checked(result)
    assert expected in result.answer
    original = {(f"C{number}", matrix[number - 1][2]) for number in range(2, 6)}
    assert original <= {(cell.reference, cell.value) for cell in result.evidence}
    original_by_address = {f"{column}{row}": value for row, values in enumerate(matrix, 1)
                           for column, value in zip("ABCD", values)}
    assert all(cell.value == original_by_address[cell.reference] for cell in result.evidence)


def test_duplicate_group_date_is_not_implicitly_summed_or_deduplicated():
    unsafe(answer(grouped(extra=[[DATES[0], "서비스", 500, "서울"]])))


def test_identical_group_date_records_are_not_silently_treated_as_one_personnel_snapshot():
    unsafe(answer(grouped(extra=[[DATES[0], "서비스", 100, "서울"]])))


def test_group_with_only_one_period_cannot_disappear_from_all_group_comparison():
    matrix = grouped()
    matrix = [matrix[0], *[row for row in matrix[1:] if row[1] != "개발"],
              [DATES[1], "개발", 100, "서울"]]
    unsafe(answer(matrix))


def test_numeric_condition_filters_values_before_trajectory_calculation():
    result = answer([["Date", "인원"], ["2023-12-31", 50],
                     [DATES[2], 120], [DATES[0], 100], [DATES[1], 150]],
                    "인원 100 이상인 기간만 추이를 설명해줘")
    checked(result)
    assert "3개 관측값" in result.answer and "100명 → 120명" in result.answer
    assert "2023-12-31" not in result.answer


@pytest.mark.parametrize("field, values", [
    ("Company", ["A", "B", "A"]), ("Scenario", ["Actual", "Forecast", "Actual"]),
    ("Currency", ["USD", "EUR", "USD"]),
])
def test_unrequested_identity_dimension_must_not_be_merged(field, values):
    matrix = [["Date", "부서", "인원", "사업장", field],
              *[[date, "서비스", count, "서울", value]
                for date, count, value in zip(DATES, [100, 80, 90], values)]]
    unsafe(answer(matrix))


@pytest.mark.parametrize("column, value", [(0, None), (1, None), (2, None), (2, "=EXTERNAL()"), (3, None)])
def test_unresolved_requested_population_cannot_be_silently_dropped(column, value):
    matrix = grouped()
    matrix[2][column] = value
    unsafe(answer(matrix))


@pytest.mark.parametrize("question", [
    "대전 사업장만 부서별 인원 추이를 비교해줘",
    "서울 또는 부산 사업장만 부서별 인원 추이를 비교해줘",
    "서울 사업장만 부서별 인원 추이와 내년 예상 인원을 설명해줘",
])
def test_unknown_or_unimplemented_condition_cannot_receive_verified_badge(question):
    unsafe(answer(grouped(), question))


def test_mixed_units_inside_group_cannot_receive_verified_badge():
    summary, index = table_fixture([(1, 1, grouped())])
    index = formats(summary, index, {"C3": "0.00%"})
    unsafe(trend_answer(QUESTION, summary, index))


def test_hidden_rows_and_incomplete_originals_are_not_complete_grouped_answers():
    summary, index = table_fixture([(1, 1, grouped())])
    summary.sheets[0].regions[0].hidden_rows.append(3)
    unsafe(trend_answer(QUESTION, summary, index))
    summary, index = table_fixture([(1, 1, grouped())])
    index = replace(index, rows=index.rows[:-1], truncated=True,
                    truncated_sheet_names=frozenset({"Arbitrary"}))
    unsafe(trend_answer(QUESTION, summary, index))
