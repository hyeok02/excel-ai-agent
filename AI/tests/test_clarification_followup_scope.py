import asyncio

from app.agent.query.conversation_models import QuestionConversation
from app.agent.query.conversation_choices import _replace_operation
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter
from tests.support.clarification_fixtures import fixture, initial, QueryClassifier, selection, service
from tests.tabular_query_fixtures import table_fixture


def test_operation_followup_keeps_original_selected_filter():
    summary, index = fixture()
    table = build_query_tables(summary)[0]
    original = initial(summary, index, "Record가 One인 Revenue 합계는?")
    option = original.clarification_options[1]
    filters = [TabularFilter(column_id="A", operator="equals", value="One")]
    classifier = QueryClassifier(table, "C", filters=filters)
    chosen = asyncio.run(service(classifier).answer(option.question, summary, index, selection(original, option)))
    assert "합계 100" in chosen.answer
    context = QuestionConversation(turns=[{
        "question": chosen.resolved_question,
        "evidence": [f"{item.sheet_name}!{item.reference}" for item in chosen.evidence][:12],
    }])
    average = QueryClassifier(table, "C", "average", filters)
    result = asyncio.run(service(average).answer("그 항목 평균은?", summary, index, context))
    assert "One" in result.resolved_question and "EUR" in result.resolved_question
    assert "평균 100" in result.answer and "150" not in result.answer
    assert result.verification.level == "source_checked"


def test_operation_rewrite_never_changes_source_label_or_record_identity():
    summary, _ = table_fixture([(1, 1, [
        ["Record", "Total Revenue"], ["Sum Fund", 10], ["Other", 20],
    ])])
    table = build_query_tables(summary)[0]
    assert _replace_operation("Sum Fund의 Total Revenue 합계는?", "평균", table) == "Sum Fund의 Total Revenue 평균는?"
    assert _replace_operation("Sum Fund의 Total Revenue는?", "평균", table) is None
    assert _replace_operation("Total Revenue의 sum", "평균", table) == "Total Revenue의 평균"
    assert _replace_operation("Total Revenue 합계와 평균", "최대", table) is None
