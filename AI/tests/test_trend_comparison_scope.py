"""Explicit related metric labels remain distinct from ambiguous source copies."""
import pytest

from app.agent.query.trend_comparison import comparison_answer
from app.agent.query.trend_selection import prepare_trend_candidate
from app.agent.query.trend_sources import trend_candidates
from tests.support.large_workbook_fixtures import offline
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("other", [[100, 120], [20, 30]])
def test_explicit_related_labels_stay_two_metrics_even_with_identical_values(other):
    summary, index = table_fixture([(1, 1, [["Date", "Total Employees", "Employees"],
        ["2024-01-01", 100, other[0]], ["2024-02-01", 120, other[1]]])])
    question = "Employees와 Total Employees의 기간별 추이를 비교해줘"
    prepared = [prepare_trend_candidate(candidate, index.rows)
                for candidate in trend_candidates(summary, index, question)]
    answer = comparison_answer(question, prepared, index.rows, set(), summary, index)
    assert answer.verification.level == "request_checked"
    assert "Total Employees:" in answer.answer and "\nEmployees:" in answer.answer
    assert "마지막 관측값 차이(Total Employees - Employees)" in answer.answer


def test_competing_unknown_date_axis_downgrades_without_direct_numeric_comparison():
    summary, index = table_fixture([(1, 1, [["Date", "Total Employees", "Temporary Employees"],
        ["2024-01-01", 100, 20], ["2024-02-01", 120, 30]])])
    question = "Total Employees와 Temporary Employees의 기간별 추이를 비교해줘"
    prepared = [prepare_trend_candidate(candidate, index.rows)
                for candidate in trend_candidates(summary, index, question)]
    answer = comparison_answer(question, prepared, index.rows, set(), summary, index, scope_ambiguous=True)
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert "alternative_source_ambiguous" in answer.verification.checks
    assert "request_alignment" not in answer.verification.checks
    assert "마지막 관측값 차이" not in answer.answer
