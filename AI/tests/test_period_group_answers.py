"""A total by month/quarter/year over a column of dates is computed per calendar period."""
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_routing import planned_tabular_answer
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Date", "Region", "Amount"], ["2024-01-05T00:00:00", "East", 10], ["2024-01-20T00:00:00", "West", 5],
        ["2024-02-03T00:00:00", "East", 7], ["2024-04-11T00:00:00", "East", 20], ["2025-01-02T00:00:00", "West", 1]]


def _ask(question, operation="numeric_summary", group="Date", filters=(), rows=ROWS):
    summary, index = table_fixture([(1, 1, rows)], sheet_name="Sales")
    table = build_query_tables(summary)[0]
    ids = {column.header: column.id for column in table.columns}
    plan = TabularQueryPlan(operation=operation, table_id=table.id, group_by=[ids[group]],
                            column_ids=[ids["Amount"]] if operation == "numeric_summary" else [], statistic="sum",
                            filters=[TabularFilter(column_id=ids[name], operator="equals", value=value) for name, value in filters])
    return planned_tabular_answer(QuestionIntent(False, "aggregation", (), True, plan), summary, index, question)


def test_dates_are_bucketed_by_the_asked_calendar_grain_in_time_order():
    assert _ask("월별 금액 알려줘").answer == "월별 ‘Amount’ 합계: 2024년 1월 15, 2024년 2월 7, 2024년 4월 20, 2025년 1월 1."
    assert _ask("분기별 금액 알려줘").answer == "분기별 ‘Amount’ 합계: 2024년 1분기 22, 2024년 2분기 20, 2025년 1분기 1."
    assert _ask("연도별 건수", operation="row_count").answer == "연도별 행 수: 2024년 4, 2025년 1."
    assert _ask("동부 월별 금액", filters=[("Region", "East")]).answer.startswith("월별 ‘Amount’ 합계: 2024년 1월 10,")


def test_the_noun_asked_for_names_the_grain_and_the_top_period_leads():
    assert _ask("금액이 가장 많은 달은?").answer.startswith("가장 큰 달은 2024년 4월입니다 (‘Amount’ 합계 20). 월별")


def test_another_grouping_or_dates_already_one_per_period_keep_the_plan():
    assert "period_group_query" not in _ask("월별 금액 알려줘", group="Region").selected_tools
    monthly = [["Date", "Region", "Amount"], ["2024-01-01T00:00:00", "East", 1], ["2024-02-01T00:00:00", "East", 2]]
    assert "period_group_query" not in _ask("월별 금액 알려줘", rows=monthly).selected_tools
    assert "period_group_query" not in _ask("금액 합계를 해줘").selected_tools


def test_other_wordings_name_the_grain_and_a_total_without_grouping_is_never_held_back():
    assert _ask("매달 금액 알려줘").answer.startswith("월별 ‘Amount’ 합계: 2024년 1월 15,")
    assert _ask("해마다 금액 알려줘").answer == "연도별 ‘Amount’ 합계: 2024년 42, 2025년 1."
    summary, index = table_fixture([(1, 1, ROWS)], sheet_name="Sales")
    table = build_query_tables(summary)[0]
    amount = next(column.id for column in table.columns if column.header == "Amount")
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=[amount], statistic="sum")
    answer = planned_tabular_answer(QuestionIntent(False, "aggregation", (), True, plan), summary, index, "연간 금액 합계는?")
    assert answer.status != "insufficient_evidence" and "43" in answer.answer
