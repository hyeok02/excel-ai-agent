"""An LLM-selected header relation never outranks the actual question/source."""
from dataclasses import replace

import pytest

from app.agent.query.header_relation_answers import header_relation_answer
from app.agent.query.header_relation_models import HeaderRelationPlan
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from tests.tabular_query_fixtures import table_fixture

QUESTION = "Orion과 Vega 작업이 같은 거야?"


def _answer(summary, index, question=QUESTION, mentions=None, **overrides):
    table = build_query_tables(summary)[0]
    plan = HeaderRelationPlan(**{
        "table_id": table.id, "column_ids": [table.columns[1].id],
        "mentions": mentions or ["Orion", "Vega 작업"], **overrides,
    })
    return header_relation_answer(question, summary, index,
                                  QuestionIntent(False, "field_relation", header_relation=plan))


def _not_a_verified_relation(result):
    assert result is None or result.verification.level == "unverified", result
    if result is not None:
        assert result.status == "insufficient_evidence", result.answer
        assert "같은 작업입니다" not in result.answer


@pytest.mark.parametrize("headers,records", [
    (["Record", "Notes"], [["R1", "Orion, Vega 작업"], ["R2", "other"]]),
    (["Record", "Orion, Lyra 작업"], [["R1", "yes"], ["R2", "no"]]),
    (["Record", "Orion, Vega 작업"], [["R1", "yes"], ["R2", "no"]]),
])
def test_data_values_missing_terms_and_invented_columns_cannot_prove_a_header_relation(headers, records):
    summary, index = table_fixture([(1, 1, [headers, *records])])
    overrides = {"column_ids": ["ZZ"]} if headers[1] == "Orion, Vega 작업" else {}
    _not_a_verified_relation(_answer(summary, index, **overrides))


def test_fabricated_table_id_cannot_select_a_real_header():
    summary, index = table_fixture([(1, 1, [["Record", "Orion, Vega 작업"], ["R1", "yes"]])])
    _not_a_verified_relation(_answer(summary, index, table_id="Imaginary!A1:B9"))


@pytest.mark.parametrize("question", [
    "Orion과 Vega 작업의 합계는 같아?",
    "Orion과 Vega 작업의 평균 수치를 비교해줘",
    "Orion과 Vega 작업은 각각 몇 건이야?",
    "Orion과 Vega 작업의 표시별 건수를 요약해줘",
])
def test_relation_plan_does_not_replace_calculation_requests(question):
    summary, index = table_fixture([(1, 1, [["Record", "Orion, Vega 작업"], ["R1", 10], ["R2", 20]])])
    _not_a_verified_relation(_answer(summary, index, question))


def test_plan_mentions_must_be_requested_not_just_exist_in_header():
    summary, index = table_fixture([(1, 1, [["Record", "Orion, Vega 작업"], ["R1", "yes"]])])
    _not_a_verified_relation(_answer(summary, index, "Atlas와 Lyra 작업은 같은 거야?"))


@pytest.mark.parametrize("mentions,header,question", [
    (["Orion", "Orion 작업"], "Orion 작업", "Orion과 Orion 작업은 같은 거야?"),
    (["Orion", "Orion"], "Orion, Vega 작업", "Orion과 Vega 작업은 같은 거야?"),
    (["Ion", "Vega 작업"], "Orion, Vega 작업", "Ion과 Vega 작업은 같은 거야?"),
])
def test_overlapping_duplicate_or_partial_tokens_do_not_prove_two_source_entities(mentions, header, question):
    summary, index = table_fixture([(1, 1, [["Record", header], ["R1", "yes"]])])
    try:
        result = _answer(summary, index, question, mentions)
    except ValueError:
        return  # A strict plan schema may reject duplicate/overlapping mentions early.
    _not_a_verified_relation(result)


def test_multiple_candidate_tables_cannot_be_disambiguated_by_model_choice_alone():
    summary, index = table_fixture([
        (1, 1, [["Record", "Orion, Vega 작업"], ["R1", "yes"]]),
        (7, 4, [["Record", "Orion 작업", "Vega 작업"], ["R2", "yes", "no"]]),
    ])
    _not_a_verified_relation(_answer(summary, index))


def test_summary_header_must_still_match_original_indexed_cell():
    summary, index = table_fixture([(1, 1, [["Record", "Orion, Vega 작업"], ["R1", "yes"]])])
    index = replace(index, rows=tuple(replace(row, cells=tuple(
        replace(cell, value="Unrelated source") if cell.address == "B1" else cell
        for cell in row.cells)) for row in index.rows))
    _not_a_verified_relation(_answer(summary, index))


def test_classifier_unavailable_does_not_turn_value_comparison_into_header_placement():
    summary, index = table_fixture([(1, 1, [
        ["ID", "매출", "비용"], ["R1", 10, 10], ["R2", 20, 15],
    ])])
    assert header_relation_answer("매출과 비용이 같은지 비교해줘", summary, index, QuestionIntent(False)) is None
    structural = header_relation_answer("매출과 비용은 같은 항목이야?", summary, index, QuestionIntent(False))
    assert structural.status == "limited"
    assert structural.verification.level == "source_checked"


@pytest.mark.parametrize("question", [
    "매출과 비용이 같은 행만 알려줘", "매출과 비용의 차이가 얼마나 나?", "매출과 비용이 같은지 비교해줘",
])
def test_explicit_model_comparison_is_not_replaced_by_header_explanation(question):
    summary, index = table_fixture([(1, 1, [
        ["Record", "매출", "비용"], ["R1", 10, 10], ["R2", 20, 15],
    ])])
    intent = QuestionIntent(False, "comparison", from_model=True)
    assert header_relation_answer(question, summary, index, intent) is None


@pytest.mark.parametrize("question", [
    "매출과 비용 수식의 차이는?", "매출과 비용이 같은 행만 알려줘", "매출과 비용의 차이는 얼마야?",
])
def test_bad_field_relation_classifier_cannot_override_formula_row_or_amount_requests(question):
    summary, index = table_fixture([(1, 1, [
        ["Record", "매출", "비용"], ["R1", 10, 10], ["R2", 20, 15],
    ])])
    table = build_query_tables(summary)[0]
    plan = HeaderRelationPlan(table_id=table.id, column_ids=["B", "C"], mentions=["매출", "비용"])
    intent = QuestionIntent(False, "field_relation", from_model=True, header_relation=plan)
    assert header_relation_answer(question, summary, index, intent) is None
