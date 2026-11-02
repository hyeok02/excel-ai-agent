"""A clicked option is honoured even when only a model plan produced the choice."""
import asyncio

from app.agent.query import clarification_selection
from app.agent.query.tabular_advanced_language import advanced_operations_match
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.support.clarification_fixtures import fixture, initial, QueryClassifier, selection, service
from tests.tabular_query_fixtures import table_fixture


def test_an_option_not_reproduced_without_the_plan_is_matched_from_its_named_table(monkeypatch) -> None:
    summary, index = fixture()
    answer = initial(summary, index)
    option = answer.clarification_options[1]
    # The question alone (no model plan) no longer yields these candidates.
    monkeypatch.setattr(clarification_selection, "trend_answer", lambda *args: None)
    monkeypatch.setattr(clarification_selection, "ambiguous_source_answer", lambda *args: None)

    classifier = QueryClassifier(build_query_tables(summary)[0], "C")
    result = asyncio.run(service(classifier).answer(option.question, summary, index, selection(answer, option)))
    assert "300" in result.answer and "select_source_scope" in result.selected_tools


def test_a_tampered_option_is_still_rejected_without_a_model_call(monkeypatch) -> None:
    summary, index = fixture()
    answer = initial(summary, index)
    option = answer.clarification_options[1]
    monkeypatch.setattr(clarification_selection, "ambiguous_source_answer", lambda *args: None)
    context = selection(answer, option)
    context.selection.option_id = "0" * 64

    result = asyncio.run(service().answer(option.question, summary, index, context))
    assert result.status == "insufficient_evidence" and result.selected_tools == ["clarify_source_scope"]


def test_share_wording_over_a_stored_share_column_names_the_field() -> None:
    summary, _ = table_fixture([(1, 1, [
        ["Rank", "Holder", "Percent Held (%)", "Shares Held"], [1, "A", 9.5, 950], [2, "B", 8.5, 850],
    ])])
    table = build_query_tables(summary)[0]
    stored = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["C"], statistic="sum")
    amounts = stored.model_copy(update={"column_ids": ["D"]})

    assert advanced_operations_match("상위 2개 보유자 비중 합계는?", stored, table)
    assert not advanced_operations_match("상위 2개 보유자 비중 합계는?", amounts, table)
