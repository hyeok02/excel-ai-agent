"""Independent scopes, original readback, and generic schema binding."""
from dataclasses import replace

import pytest

from app.agent.query.trend_answers import trend_answer
from tests.support.large_workbook_fixtures import offline, parsed, tiny_caps, workbook
from tests.tabular_query_fixtures import table_fixture
from tests.test_grouped_trend_adversarial import DATES, QUESTION, answer, checked, grouped, unsafe


def test_grouped_period_bound_discards_only_known_outside_invalid_metrics():
    checked(answer(grouped(extra=[["2023-12-31", "서비스", None, "서울"]]), "2024년 1분기 " + QUESTION))


def test_numeric_predicate_does_not_validate_outside_absolute_period():
    matrix = [["Date", "인원"], ["2023-12-31", None], *zip(DATES, [100, 150, 120])]
    checked(answer(matrix, "2024년 1분기 인원 100 이상인 기간만 추이를 설명해줘"))


def test_grouping_is_independent_of_column_order_location_and_literal_names():
    matrix = [["Count", "Territory", "Date", "Role"],
              *[[value, "Harbor", date, group] for group, values in [("Alpha", [100, 80, 90]),
                                                                    ("Beta", [40, 100, 50])]
                for date, value in zip(DATES, values)]]
    summary, index = table_fixture([(8, 4, matrix)], sheet_name="Moved Records")
    result = trend_answer("Harbor Territory Count trend by Role", summary, index)
    assert result.status in {"answered", "limited"}, result.model_dump()
    assert "Alpha" in result.answer and "Beta" in result.answer
    assert "100 → 90" in result.answer and "40 → 50" in result.answer
    assert {"D9", "D14"} <= {cell.reference for cell in result.evidence}


def test_a_different_company_per_group_is_not_an_explicit_company_comparison():
    matrix = grouped()
    matrix[0].append("Company")
    for row in matrix[1:]:
        row.append("A" if row[1] == "서비스" else "B")
    unsafe(answer(matrix))


def test_explicit_second_group_dimension_preserves_company_populations():
    matrix = grouped()
    matrix[0].append("Company")
    for row in matrix[1:]:
        row.append("A" if row[1] == "서비스" else "B")
    checked(answer(matrix, "서울 사업장만 Company 및 부서별 인원 추이를 비교해줘"))


def test_group_period_gaps_are_disclosed_without_complete_verification():
    matrix = grouped()
    del matrix[2]
    result = answer(matrix)
    unsafe(result)
    assert "날짜가 다릅니다" in " ".join(result.limitations)


def test_invalid_alternative_table_must_not_disappear_because_it_has_no_numeric_values():
    invalid = grouped()
    for row in invalid[1:]:
        row[2] = None
    summary, index = table_fixture([(1, 1, grouped()), (12, 1, invalid)])
    unsafe(trend_answer(QUESTION, summary, index))
    checked(trend_answer("'Arbitrary'!A1:D7 범위에서 " + QUESTION, summary, index))


def test_all_invalid_requested_values_are_not_answered_by_other_metric():
    matrix = grouped()
    matrix[0].append("다른 수치")
    for row in matrix[1:]:
        row[2] = None
        row.append(123)
    unsafe(answer(matrix))


def test_truncated_index_reads_all_groups_and_their_tail_periods(tiny_caps):
    summary, index, _ = parsed(workbook({"Records": grouped()}))
    assert index.truncated
    checked(trend_answer(QUESTION, summary, index))


def test_tampered_summary_condition_cannot_change_selected_population():
    summary, index = table_fixture([(1, 1, grouped(extra=[[DATES[0], "서비스", 999, "부산"]]))])
    for row in summary.sheets[0].regions[0].analysis_rows:
        for cell in row:
            if cell["address"] == "D8":
                cell["value"] = "서울"
    unsafe(trend_answer(QUESTION, summary, index))


def test_streaming_source_identity_mismatch_cannot_verify_sample(tiny_caps):
    summary, index, _ = parsed(workbook({"Records": grouped()}))
    index = replace(index, source_digest="another-workbook")
    unsafe(trend_answer(QUESTION, summary, index))


@pytest.mark.parametrize("statistic", ["합계", "평균"])
def test_explicit_aggregation_does_not_combine_distinct_scenarios(statistic):
    matrix = grouped()
    matrix[0].append("Scenario")
    for index, row in enumerate(matrix[1:]):
        row.append("Actual" if index % 2 else "Forecast")
    unsafe(answer(matrix, f"서울 사업장만 부서별 인원 {statistic} 추이를 비교해줘"))
