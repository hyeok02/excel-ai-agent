"""A named period is answered for that period only, never with the whole file's total."""
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_routing import planned_tabular_answer
from app.agent.query.verified_insight_constraints import required_concepts_match
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Date", "Region", "Amount"], ["2022-12-30T00:00:00", "East", 10], ["2023-01-01T00:00:00", "East", 20],
        ["2023-06-15T00:00:00", "West", 30], ["2023-12-31T00:00:00", "West", 40], ["2024-01-01T00:00:00", "East", 50]]


def _answer(question, *bounds):
    summary, index = table_fixture([(1, 1, ROWS)])
    table = build_query_tables(summary)[0]
    filters = [TabularFilter(column_id="A", operator=operator, value=value) for operator, value in bounds]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["C"], statistic="sum",
                            filters=filters)
    return planned_tabular_answer(QuestionIntent(False, "aggregation", (), True, plan), summary, index, question)


def test_a_year_is_summed_over_exactly_that_year() -> None:
    answer = _answer("2023년 Amount 합계는?", ("greater_than_or_equal", "2023-01-01"),
                     ("less_than_or_equal", "2023-12-31"))
    assert answer.status == "answered" and "합계 90" in answer.answer, answer.answer
    half_open = _answer("2023년 Amount 합계는?", ("greater_than_or_equal", "2023-01-01T00:00:00"),
                        ("less_than", "2024-01-01"))
    assert "합계 90" in half_open.answer
    end_of_day = _answer("2023년 Amount 합계는?", ("greater_than_or_equal", "2023-01-01T00:00:00"),
                         ("less_than_or_equal", "2023-12-31T23:59:59"))
    assert "합계 90" in end_of_day.answer
    noon = _answer("2023년 Amount 합계는?", ("greater_than_or_equal", "2023-01-01"),
                   ("less_than_or_equal", "2023-12-31T12:00:00"))
    assert noon.status == "insufficient_evidence"


def test_date_filters_for_another_or_unrequested_period_stay_unproven() -> None:
    year = (("greater_than_or_equal", "2023-01-01"), ("less_than_or_equal", "2023-12-31"))
    for question in ("2022년 Amount 합계는?", "Amount 합계는?", "2023년 6월 Amount 합계는?"):
        assert _answer(question, *year).selected_tools == ["tabular_query"]
        assert _answer(question, *year).status == "insufficient_evidence"
    month = _answer("2023년 6월 Amount 합계는?", ("greater_than_or_equal", "2023-06-01"), ("less_than", "2023-07-01"))
    assert "합계 30" in month.answer


def test_a_period_bound_is_not_a_fact_about_that_year() -> None:
    whole = "이 파일은 2022년 1월 1일부터 2023년 12월 30일까지의 판매 내역입니다. 판매금액 합계는 $33,325.58입니다."
    assert not required_concepts_match("2023년 판매금액 합계는?", whole)
    assert not required_concepts_match("2023년 12월 판매금액 합계는?", whole)
    assert required_concepts_match("판매금액 합계는?", whole)
    assert required_concepts_match("2022년부터 2023년까지 판매금액 합계는?", whole)
    assert required_concepts_match("2023년 비율은?", "비율은 2022년 43%에서 2023년 40%로 감소했습니다.")
