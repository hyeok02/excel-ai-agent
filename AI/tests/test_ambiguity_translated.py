import asyncio
from dataclasses import replace

from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture
from tests.test_ambiguity_service import _service


def _duplicate_caption(monkeypatch):
    first, first_index = table_fixture([(3, 2, [
        ["HOLDER", "PERCENT HELD (%)"], ["Alpha Fund", 10], ["Beta Fund", 0.5],
    ])], sheet_name="Current population")
    second, second_index = table_fixture([(7, 5, [
        ["OWNER", "Percent Owned (%)"], ["Other Fund", 20], ["Further Fund", 0.3],
    ])], sheet_name="Comparison population")
    summary = replace(first, sheets=[*first.sheets, *second.sheets], sheet_count=2)
    index = replace(first_index, rows=(*first_index.rows, *second_index.rows))
    tables = [replace(table, context=((f"{table.sheet_name}!A1", "LEADING INVESTORS"),))
              for table in build_query_tables(summary)]
    monkeypatch.setattr("app.agent.query.ambiguity_tables.build_query_tables", lambda _: tables)
    return summary, index, tables


def test_translated_metric_and_duplicate_context_do_not_identify_one_population(monkeypatch):
    summary, index, _ = _duplicate_caption(monkeypatch)
    answer = ambiguous_source_answer("LEADING INVESTORS에서 지분율이 1% 이상인 보유자는 몇 곳이야?",
                                     summary, index)
    assert answer is not None and answer.verification.level == "unverified"
    assert "Current population" in answer.answer and "Comparison population" in answer.answer


def test_classifier_cannot_certify_wrong_population_just_because_count_agrees(monkeypatch):
    summary, index, tables = _duplicate_caption(monkeypatch)
    plan = TabularQueryPlan(operation="row_count", table_id=tables[1].id, filters=[
        TabularFilter(column_id="F", operator="greater_than_or_equal", value=1, value_unit="percent"),
    ])
    intent = QuestionIntent(False, "row_count", (), True, plan)
    answer = asyncio.run(_service(intent).answer(
        "LEADING INVESTORS에서 지분율이 1% 이상인 보유자는 몇 곳이야?", summary, index,
    ))
    assert answer.status == "insufficient_evidence" and answer.verification.level == "unverified"
    assert "1건" not in answer.answer


def test_explicit_sheet_scope_resolves_translated_metric_and_duplicate_caption(monkeypatch):
    summary, index, _ = _duplicate_caption(monkeypatch)
    assert ambiguous_source_answer(
        "Current population 시트의 LEADING INVESTORS에서 지분율이 1% 이상인 보유자는 몇 곳이야?",
        summary, index,
    ) is None


def test_translated_metric_does_not_collapse_different_qualified_measure(monkeypatch):
    summary, index = table_fixture([(1, 1, [["Entity", "Revenue Growth", "Revenue Per Employee"],
                                           ["Example", 5, 10]])])
    assert ambiguous_source_answer("매출은 얼마야?", summary, index) is None


def test_explicit_exact_field_wins_over_broad_translated_aliases():
    summary, index = table_fixture([(1, 1, [["Entity", "Total Debt", "Total Liabilities"],
                                           ["Example", 5, 10]])])
    assert ambiguous_source_answer("총부채(Total Debt) 합계는?", summary, index) is None
