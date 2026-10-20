"""Independent denominator audit for categorical shares, with no AI calls."""
import pytest

from app.agent.query.grouped_share_trend_answers import grouped_share_trend_answer
from tests.support.large_workbook_fixtures import offline
from tests.support.trend_scoped_fixtures import formats
from tests.tabular_query_fixtures import table_fixture
from tests.test_grouped_share_trend import ROWS, answer as category_answer


@pytest.mark.parametrize("label", ["EPS", "Revenue per Employee", "주당이익", "1인당 매출"])
def test_per_unit_metrics_cannot_be_summed_into_an_unweighted_whole(label):
    summary, index = table_fixture([(1, 1, [["Date", "부서", label],
        ["2024-01-31", "서비스", 20], ["2024-01-31", "생산", 80],
        ["2024-02-29", "서비스", 30], ["2024-02-29", "생산", 70]])])
    index = formats(summary, index, {f"C{number}": "$0.00" for number in range(2, 6)})
    answer = grouped_share_trend_answer(f"전체 {label} 중 서비스 부서 비중 추이", summary, index)
    assert answer is not None and answer.status == "insufficient_evidence", answer
    assert answer.verification.level == "unverified"


@pytest.mark.parametrize("total_label", ["계", "누계"])
def test_common_total_rows_cannot_double_count_the_denominator(total_label):
    rows = [*ROWS, *[[date, total_label, 100] for date in ("2024-01-31", "2024-02-29", "2024-03-31")]]
    answer = category_answer(rows)
    assert answer.status == "insufficient_evidence", answer.model_dump()
    assert answer.verification.level == "unverified"
