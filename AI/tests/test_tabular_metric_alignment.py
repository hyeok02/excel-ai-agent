from dataclasses import replace

import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("question", ["매출 합계", "Revenue 합계", "매출액을 합계로 알려줘"])
def test_translated_metric_cannot_be_replaced_by_another_numeric_column(question):
    summary, index = table_fixture([(4, 3, [
        ["Customer", "Revenue", "Debt"], ["North", 10, 20], ["South", 15, 30],
    ])])
    table = build_query_tables(summary)[0]
    wrong = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                             column_ids=["E"], statistic="sum")
    assert execute_tabular_query(wrong, summary, index, question) is None
    correct = wrong.model_copy(update={"column_ids": ["D"]})
    answer = execute_tabular_query(correct, summary, index, question)
    assert answer is not None and "합계 25" in answer.answer


def test_translated_metric_cannot_be_replaced_by_an_unrelated_table():
    summary, index = table_fixture([
        (1, 1, [["Item", "Revenue"], ["North", 10], ["South", 15]]),
        (1, 5, [["Item", "Debt"], ["North", 20], ["South", 30]]),
    ])
    tables = build_query_tables(summary)
    wrong = TabularQueryPlan(operation="numeric_summary", table_id=tables[1].id,
                             column_ids=["F"], statistic="sum")
    assert execute_tabular_query(wrong, summary, index, "매출 합계") is None


def test_named_source_caption_and_ranking_grammar_do_not_add_unrequested_metrics(monkeypatch):
    summary, index = table_fixture([
        (1, 1, [["Rank", "Percent Held (%)"], [1, 10], [2, 8], [3, 5]]),
        (1, 5, [["Item", "Percent Owned (%)"], ["North", 40], ["South", 60]]),
    ])
    tables = build_query_tables(summary)
    tables = [replace(tables[0], context=(("Arbitrary!A1", "TOP 30 HOLDERS"),)), tables[1]]
    monkeypatch.setattr("app.agent.query.tabular_execution.build_query_tables", lambda _: tables)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=tables[0].id,
                            column_ids=["B"], order_by="B", limit=2, statistic="sum")
    result = execute_tabular_query(plan, summary, index, "TOP 30 HOLDERS의 상위 2개 지분율 합계")
    assert result is not None and "합계 18" in result.answer
