"""A threshold written with a counter is read, and a refusal citing cells still lets the last stages try."""
from types import SimpleNamespace

from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.series_binding import answers_nothing
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


def test_a_counter_between_the_number_and_the_comparison_is_part_of_the_threshold():
    summary, index = table_fixture([(1, 1, [["Item", "Qty"], ["A", 150], ["B", 90], ["C", 100]])])
    table = build_query_tables(summary)[0]
    plan = lambda value: TabularQueryPlan(operation="row_count", table_id=table.id, column_ids=[], statistic="all",
                                          filters=[TabularFilter(column_id="B", operator="greater_than_or_equal", value=value)])
    assert "2건" in execute_tabular_query(plan(100), summary, index, "Qty가 100개 이상인 건수는?").answer
    assert execute_tabular_query(plan(10), summary, index, "Qty가 100개 이상인 건수는?") is None


def test_a_refusal_citing_cells_or_an_unknown_reading_answers_nothing():
    answer = lambda status, evidence=(), checks=(), options=(): SimpleNamespace(
        status=status, evidence=list(evidence), clarification_options=list(options),
        verification=SimpleNamespace(checks=list(checks)))
    assert answers_nothing(answer(QuestionAnswerStatus.INSUFFICIENT_EVIDENCE, evidence=["cell"]))
    assert answers_nothing(answer(QuestionAnswerStatus.LIMITED, checks=["question_unanswered"]))
    assert not answers_nothing(answer(QuestionAnswerStatus.LIMITED, evidence=["cell"]))
    assert not answers_nothing(answer(QuestionAnswerStatus.INSUFFICIENT_EVIDENCE, evidence=["cell"], options=["pick"]))
    assert not answers_nothing(answer(QuestionAnswerStatus.INSUFFICIENT_EVIDENCE))  # handled as before
