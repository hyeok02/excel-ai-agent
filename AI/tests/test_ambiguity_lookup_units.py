import asyncio

import pytest

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture
from tests.test_ambiguity_service import _service


@pytest.mark.parametrize("operation,kind", [("lookup", "cell_lookup"), ("row_list", "row_list")])
@pytest.mark.parametrize("question", ["R001의 EUR 기준 Amount값", "R001의 Amount를 EUR로 환산해서 알려줘"])
def test_unit_base_lookup_cannot_verify_an_unsupported_currency(operation, kind, question):
    summary, index = table_fixture([(1, 1, [["Record", "Amount (USD)"], ["R001", 10]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation=operation, table_id=table.id, column_ids=["Amount"],
                            filters=[TabularFilter(column_id="Record", operator="equals", value="R001")])
    answer = asyncio.run(_service(QuestionIntent(False, kind, (), True, plan)).answer(question, summary, index))
    assert answer.verification.level != "request_checked"


def test_row_count_of_currency_category_is_not_a_requested_output_conversion():
    summary, index = table_fixture([(1, 1, [["Currency", "Amount (USD)"], ["EUR", 10], ["USD", 20]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_count", table_id=table.id,
                            filters=[TabularFilter(column_id="Currency", operator="equals", value="EUR")])
    answer = asyncio.run(_service(QuestionIntent(False, "row_count", (), True, plan)).answer(
        "Currency가 EUR인 건수는?", summary, index,
    ))
    assert answer.status == "answered" and answer.verification.level == "request_checked"


def test_source_unit_lookup_does_not_require_identity_column_to_have_currency():
    summary, index = table_fixture([(1, 1, [["Record", "Amount (USD)"], ["R001", 10]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=["Record", "Amount"],
                            filters=[TabularFilter(column_id="Record", operator="equals", value="R001")])
    answer = asyncio.run(_service(QuestionIntent(False, "cell_lookup", (), True, plan)).answer(
        "R001의 Record와 USD 기준 Amount는?", summary, index,
    ))
    assert answer.status == "answered" and answer.verification.level == "request_checked"
