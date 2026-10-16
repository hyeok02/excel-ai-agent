import asyncio

import pytest

from app.agent.query.ambiguity_labels import label_base, resolve_unique_column, source_mentioned
from app.agent.query.ambiguity_tables import table_candidates
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture
from tests.test_ambiguity_service import _service


@pytest.mark.parametrize("header", ["Net Revenue (USD millions)", "Net Revenue [USD]",
                                    "Net Revenue（KRW）", "Net Revenue (in EUR thousands)"])
def test_complete_base_label_can_bind_one_unit_qualified_source_column(header):
    summary, _ = table_fixture([(1, 1, [["Record", header], ["Example", 10]])])
    table = build_query_tables(summary)[0]
    assert label_base(header) == "Net Revenue"
    assert resolve_unique_column("net revenue", table) == "B"


@pytest.mark.parametrize("qualifier", ["min", "bin", "in", "2025", "forecast", "per share"])
def test_nonunit_qualifiers_are_not_stripped_or_guessed(qualifier):
    header = f"Revenue ({qualifier})"
    summary, _ = table_fixture([(1, 1, [["Record", header], ["Example", 10]])])
    table = build_query_tables(summary)[0]
    assert label_base(header) == header
    assert resolve_unique_column("Revenue", table) is None


def test_competing_units_and_partial_measure_names_do_not_bind():
    summary, _ = table_fixture([(1, 1, [["Record", "Revenue (USD)", "Revenue (EUR)"],
                                       ["Example", 10, 20]])])
    table = build_query_tables(summary)[0]
    assert resolve_unique_column("revenue", table) is None
    assert resolve_unique_column("Revenue (JPY)", table) is None
    assert resolve_unique_column("Rev", table) is None


def test_unit_omitted_model_column_is_computed_and_verified_from_unique_source():
    summary, index = table_fixture([(1, 1, [["Record", "Amount (USD)"], ["Alpha", 10], ["Beta", 20]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["Amount"], statistic="sum")
    answer = asyncio.run(_service(QuestionIntent(False, "aggregation", (), True, plan)).answer(
        "Amount 합계는?", summary, index,
    ))
    assert answer.status == "answered"
    assert answer.verification.level == "request_checked"
    assert "30" in answer.answer


@pytest.mark.parametrize("question", ["현황에서의 Amount 합계", "현황으로의 이동", "현황에는?", "현황과의 비교"])
def test_complete_korean_source_name_accepts_bounded_compound_particles(question):
    assert source_mentioned("현황", question)


@pytest.mark.parametrize("source,question", [("현황", "현황판의 Amount"),
                                             ("Revenue", "RevenueGrowth"),
                                             ("Revenue", "Revenue증감률"),
                                             ("North", "Northwest의 Amount")])
def test_source_phrase_cannot_match_a_longer_word_or_measure(source, question):
    assert not source_mentioned(source, question)


def test_explicit_lowercase_column_selects_same_coordinate_as_uppercase():
    summary, index = table_fixture([(1, 1, [["Record", "Amount", "Amount"], ["One", 5, 9]])])
    assert len(table_candidates("Amount는?", summary, index)) == 2
    assert table_candidates("b열 Amount는?", summary, index) == []
