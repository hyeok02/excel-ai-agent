"""request_alignment means the planned operation can produce the requested
quantity; a count, list or one-period total is not a sum, mean or change."""
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


def _table(rows=None):
    summary, index = table_fixture([(1, 1, rows or [
        ["Owner", "Year", "Amount", "Grade"], ["Alpha", 2024, 10, "평균 이하"],
        ["Beta", 2025, 20, "우수"], ["Total", None, 30, None],
    ])])
    return summary, index, build_query_tables(summary)[0]


def _run(question, **plan):
    summary, index, table = _table(plan.pop("rows", None))
    return execute_tabular_query(TabularQueryPlan(table_id=table.id, **plan), summary, index, question)


def test_counts_lists_and_distributions_do_not_answer_statistics():
    for question in ["합계는?", "총합 알려줘", "Amount 평균은?", "최댓값은?"]:
        assert _run(question, operation="row_count") is None
        assert _run(question, operation="row_list", column_ids=["A"]) is None
        assert _run(question, operation="frequencies", column_ids=["A"]) is None
    assert _run("몇 건이야?", operation="row_list", column_ids=["A"]) is None
    assert _run("Amount 평균은?", operation="numeric_summary", column_ids=["C"], statistic="sum") is None


def test_one_period_total_does_not_answer_a_change():
    for question in ["Amount 증감 알려줘", "Amount 변화 알려줘", "Amount 추이는?"]:
        assert _run(question, operation="numeric_summary", column_ids=["C"], statistic="sum") is None
        assert _run(question, operation="row_count") is None


def test_count_totals_grouped_trends_and_source_labels_still_answer():
    assert "3건" in _run("건수 합계 알려줘", operation="row_count").answer
    assert "2건" in _run("how many rows in total?", operation="row_count",
                        rows=[["Owner", "Amount"], ["A", 1], ["B", 2]]).answer
    grouped = _run("Year별 Amount 합계 추이", operation="numeric_summary", column_ids=["C"],
                   group_by=["B"], statistic="sum", rows=[["Owner", "Year", "Amount"],
                                                          ["Alpha", 2024, 10], ["Beta", 2025, 20]])
    assert grouped is not None and grouped.verification.level == "request_checked"
    total = _run("Total Amount 합계 알려줘", operation="lookup", column_ids=["C"],
                 filters=[TabularFilter(column_id="A", operator="equals", value="Total")])
    assert "30" in total.answer
    grade = _run("평균 이하 등급 Owner 목록", operation="row_list", column_ids=["A"],
                 filters=[TabularFilter(column_id="D", operator="equals", value="평균 이하")])
    assert "Alpha" in grade.answer and "Beta" not in grade.answer
    change = _run("Alpha 증감 알려줘", operation="lookup", column_ids=["B"], rows=[
        ["Owner", "전년 대비 증감"], ["Alpha", 5], ["Beta", -3]],
        filters=[TabularFilter(column_id="A", operator="equals", value="Alpha")])
    assert "5" in change.answer


def test_requested_statistics_still_match_numeric_summaries():
    rows = [["Owner", "Year", "Amount", "Grade"], ["Alpha", 2024, 10, "ordinary"],
            ["Beta", 2025, 20, "ordinary"], ["Gamma", 2026, 30, "ordinary"]]
    assert "합계 60" in _run("합계는?", operation="numeric_summary", column_ids=["C"], statistic="sum", rows=rows).answer
    assert "평균 20" in _run("Amount 평균은?", operation="numeric_summary", column_ids=["C"],
                            statistic="average", rows=rows).answer
    assert "3건" in _run("몇 건이야?", operation="row_count").answer
