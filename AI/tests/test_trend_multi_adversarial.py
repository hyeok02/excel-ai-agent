"""Explicit metric comparisons must retain every requested source population."""
import pytest

from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import checked, direct, not_certified
from tests.support.trend_scoped_fixtures import formats
from tests.tabular_query_fixtures import table_fixture

QUESTION = "2024년 Total Employees와 Temporary Employees의 기간별 추이를 비교해줘"


def _source(temporary=20, *, outside=False):
    matrix = [["Date", "Total Employees", "Temporary Employees", "Revenue"],
              ["2024-01-31", 100, 10, 7000], ["2024-02-29", 150, temporary, 8000],
              ["2024-03-31", 120, 50, 9000]]
    if outside:
        matrix.insert(1, ["2023-12-31", None, None, 99999])
    return table_fixture([(1, 1, matrix)])


@pytest.mark.parametrize("outside", [False, True])
def test_two_explicit_metrics_are_answered_together_without_unrequested_metric(outside):
    summary, index = _source(outside=outside)
    answer = direct(summary, index, QUESTION)
    checked(answer)
    assert "Total Employees" in answer.answer and "Temporary Employees" in answer.answer
    assert "100" in answer.answer and "120" in answer.answer and "50" in answer.answer
    assert "Revenue" not in answer.answer and "9,000" not in answer.answer
    assert "2023-12-31" not in answer.answer
    cited = {item.reference for item in answer.evidence}
    assert "B1" in cited and "C1" in cited


@pytest.mark.parametrize("missing", [None, "unknown", True])
def test_bad_requested_metric_does_not_leave_the_other_one_fully_verified(missing):
    summary, index = _source(missing)
    not_certified(direct(summary, index, QUESTION))


def test_request_for_unknown_third_metric_cannot_be_dropped():
    summary, index = _source()
    question = "2024년 Total Employees, Temporary Employees와 MissingMetric의 추이를 비교해줘"
    not_certified(direct(summary, index, question))


def test_unit_change_in_one_requested_metric_cannot_certify_a_complete_comparison():
    summary, index = _source()
    index = formats(summary, index, {"C3": "0.00%"})
    not_certified(direct(summary, index, QUESTION))


def test_ambiguous_duplicate_metric_cannot_be_resolved_by_dropping_a_population():
    first = [["Date", "Total Employees", "Temporary Employees"],
             ["2024-01-31", 100, 10], ["2024-02-29", 150, 20], ["2024-03-31", 120, 50]]
    other = [["Date", "Temporary Employees"],
             ["2024-01-31", 710], ["2024-02-29", 720], ["2024-03-31", 750]]
    summary, index = table_fixture([(1, 1, first), (7, 1, other)])
    not_certified(direct(summary, index, QUESTION))


def test_single_metric_question_never_expands_into_another_source_column():
    summary, index = _source()
    answer = direct(summary, index, "2024년 Total Employees의 기간별 추이를 설명해줘")
    checked(answer)
    assert "Temporary Employees" not in answer.answer and "Revenue" not in answer.answer


def test_multi_metric_question_cannot_hide_unsupported_filter():
    summary, index = _source()
    question = "2024년 Total Employees가 130 이상인 기간의 Total Employees와 Temporary Employees 추이를 비교해줘"
    not_certified(direct(summary, index, question))


@pytest.mark.parametrize("other_label", ["Temporary Employees", "Employees", "직원 수"])
def test_requested_metric_only_outside_period_cannot_disappear_as_irrelevant(other_label):
    current = [["Date", "Total Employees"], ["2024-01-31", 100],
               ["2024-02-29", 150], ["2024-03-31", 120]]
    older = [["Date", other_label], ["2023-01-31", 710],
             ["2023-02-28", 720], ["2023-03-31", 750]]
    summary, index = table_fixture([(1, 1, current), (8, 1, older)])
    question = f"2024년 Total Employees와 {other_label}의 기간별 추이를 비교해줘"
    not_certified(direct(summary, index, question))


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
@pytest.mark.parametrize("explicit_year", [False, True])
def test_years_in_both_requested_metric_names_are_not_calendar_filters(layout, explicit_year):
    matrix = [["Date", "Metric2024", "Metric2025"], ["2023-12-31", 90, 9],
              ["2024-01-31", 100, 10], ["2024-02-29", 150, 20],
              ["2024-03-31", 120, 50], ["2025-01-31", 130, 60]]
    if layout == "horizontal":
        matrix = [list(row) for row in zip(*matrix)]
        matrix[0][0] = "Metric"
    summary, index = table_fixture([(1, 1, matrix)])
    question = ("2024년 " if explicit_year else "") + "Metric2024와 Metric2025의 기간별 추이를 비교해줘"
    answer = direct(summary, index, question)
    assert answer.status in {"answered", "limited"}, answer.model_dump()
    assert "compare_trend_series" in answer.selected_tools
    assert answer.verification.level != "unverified"
    count = 3 if explicit_year else 5
    assert answer.answer.count(f"{count}개 관측값") == 2, answer.answer
    assert ("2023-12-31" in answer.answer) is not explicit_year
    assert ("2025-01-31" in answer.answer) is not explicit_year
