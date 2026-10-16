import asyncio

import pytest

from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.ambiguity_qualifiers import qualified_labels
from app.agent.query.ambiguity_tables import table_candidates
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture
from tests.test_ambiguity_service import _service


def _fixture(headers):
    return table_fixture([(1, 1, [["Record", *headers], ["Example", 10, 20], ["Another", 5, 15]])])


def _answer(question, headers, column):
    summary, index = _fixture(headers)
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=[column], statistic="sum")
    return asyncio.run(_service(QuestionIntent(False, "aggregation", (), True, plan)).answer(
        question, summary, index,
    ))


@pytest.mark.parametrize("headers,question", [
    (["Revenue (USD)", "Revenue (EUR)"], "EUR 기준 Revenue 합계는?"),
    (["Revenue [USD]", "Revenue [EUR]"], "EUR 기준 Revenue 합계는?"),
    (["Revenue (2024)", "Revenue (2025)"], "2025년 Revenue 합계는?"),
])
def test_explicit_source_qualifier_removes_needless_choice_and_computes_correct_field(headers, question):
    summary, index = _fixture(headers)
    assert ambiguous_source_answer(question, summary, index) is None
    answer = _answer(question, headers, "C")
    assert answer.status == "answered" and answer.verification.level == "request_checked"
    assert "35" in answer.answer


@pytest.mark.parametrize("headers,question", [
    (["Revenue (USD)", "Revenue (EUR)"], "EUR 기준 Revenue 합계는?"),
    (["Revenue [USD]", "Revenue [EUR]"], "EUR 기준 Revenue 합계는?"),
    (["Revenue (2024)", "Revenue (2025)"], "2025년 Revenue 합계는?"),
])
def test_wrong_model_unit_or_year_cannot_receive_verified_badge(headers, question):
    answer = _answer(question, headers, "B")
    assert answer.verification.level != "request_checked"
    assert "합계 15" not in answer.answer


@pytest.mark.parametrize("question", ["Revenue 합계", "USD와 EUR의 Revenue 합계",
                                      "Revenue를 USD에서 EUR로 환산한 합계"])
def test_omitted_or_multiple_units_and_conversion_do_not_select_one_source(question):
    summary, index = _fixture(["Revenue (USD)", "Revenue (EUR)"])
    assert len(table_candidates(question, summary, index)) == 2


@pytest.mark.parametrize("question", ["b열 Amount 합계", "B열의 Amount 합계", "column B Amount sum"])
def test_column_coordinate_selects_source_but_cannot_authorize_different_column(question):
    right = _answer(question, ["Amount", "Amount"], "B")
    assert right.verification.level == "request_checked" and "15" in right.answer
    wrong = _answer(question, ["Amount", "Amount"], "C")
    assert wrong.verification.level != "request_checked"


def test_shared_unit_keeps_distinct_source_scales_ambiguous():
    summary, index = _fixture(["Revenue (USD millions)", "Revenue (USD thousands)"])
    assert len(table_candidates("USD Revenue 합계", summary, index)) == 2


def test_one_named_qualifier_cannot_discard_an_independent_requested_measure():
    assert qualified_labels("EUR Revenue와 Cost", ["Revenue (EUR)", "Revenue (USD)", "Cost (USD)"]) == {
        "Revenue (EUR)", "Cost (USD)",
    }


@pytest.mark.parametrize("labels,question,expected", [
    (["Revenue (USD millions)", "Revenue (EUR millions)"], "USD million Revenue 합계", "Revenue (USD millions)"),
    (["Revenue (USD millions)", "Revenue (USD thousands)"], "USD million Revenue 합계", "Revenue (USD millions)"),
    (["Revenue (USD) (2024)", "Revenue (USD) (2025)"], "USD 2025년 Revenue 합계", "Revenue (USD) (2025)"),
])
def test_compound_qualifiers_match_every_explicit_dimension(labels, question, expected):
    assert qualified_labels(question, labels) == {expected}


@pytest.mark.parametrize("question", ["Item2025의 Revenue", "2025A Revenue", "CODE-2025X Revenue"])
def test_year_digits_inside_record_identifier_cannot_select_period(question):
    labels = {"Revenue (2024)", "Revenue (2025)"}
    assert qualified_labels(question, labels) == labels


def test_multiple_explicit_years_cannot_choose_only_one_period():
    labels = {"Revenue (USD) (2024)", "Revenue (USD) (2025)"}
    assert qualified_labels("USD 2024년과 2025년 Revenue 합계", labels) == labels


@pytest.mark.parametrize("question", ["EUR 기준 Amount 합계는?", "Amount를 EUR로 환산한 합계",
                                      "Amount를 USD로 환산한 합계", "JPY Amount sum"])
def test_unique_unit_base_fallback_cannot_claim_unknown_currency_or_conversion(question):
    summary, index = table_fixture([(1, 1, [["Record", "Amount (USD)"], ["Example", 10]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["Amount"], statistic="sum")
    answer = asyncio.run(_service(QuestionIntent(False, "aggregation", (), True, plan)).answer(question, summary, index))
    assert answer.verification.level != "request_checked"


def test_english_natural_column_sum_is_not_misread_as_coordinate_sum():
    from app.agent.query.ambiguity_qualifiers import explicit_column_ids

    assert explicit_column_ids("Calculate column sum of Amount") == set()
    assert explicit_column_ids("column 'ab' Amount sum") == {"AB"}
