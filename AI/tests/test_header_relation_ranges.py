"""Explicit ranges constrain both table selection and cited source headers."""
import pytest

from app.agent.query.header_relation_answers import header_relation_answer
from app.agent.query.header_relation_models import HeaderRelationPlan
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from tests.tabular_query_fixtures import table_fixture


def _fixture():
    return table_fixture([(1, 1, [
        ["Record", "Orion 작업", "Vega 작업"], ["R1", "yes", "no"], ["R2", "no", "yes"],
    ])], sheet_name="Source Sheet")


def _answer(summary, index, question, table_position=0):
    table = build_query_tables(summary)[table_position]
    plan = HeaderRelationPlan(table_id=table.id,
                              column_ids=[column.id for column in table.columns[1:]],
                              mentions=["Orion 작업", "Vega 작업"])
    intent = QuestionIntent(False, "field_relation", from_model=True, header_relation=plan)
    return header_relation_answer(question, summary, index, intent)


@pytest.mark.parametrize("scope", [
    "'Source Sheet'!A1:C1", "'Source Sheet'!B1, 'Source Sheet'!C1", "'Source Sheet'!$B$1:$C$1",
])
def test_header_row_or_individual_header_cells_can_scope_relation(scope):
    summary, index = _fixture()
    result = _answer(summary, index, f"{scope} 범위에서 Orion 작업과 Vega 작업은 같은 항목이야?")
    assert result is not None
    assert result.status == "limited", result.answer
    assert result.verification.level == "source_checked"
    assert "서로 다른 열" in result.answer
    assert {item.reference for item in result.evidence} == {"B1", "C1"}


@pytest.mark.parametrize("scope", ["'Source Sheet'!A2:C3", "'Source Sheet'!B2:C2", "'Source Sheet'!B1"])
def test_data_only_or_partial_header_ranges_do_not_cover_both_requested_headers(scope):
    summary, index = _fixture()
    result = _answer(summary, index, f"{scope} 범위에서 Orion 작업과 Vega 작업은 같은 항목이야?")
    assert result is None or (result.status == "insufficient_evidence" and result.verification.level == "unverified")


def test_exact_header_range_cannot_be_used_to_answer_about_another_table():
    summary, index = table_fixture([
        (1, 1, [["Record", "Orion 작업", "Vega 작업"], ["R1", "yes", "no"]]),
        (7, 5, [["Record", "Orion 작업", "Vega 작업"], ["R2", "no", "yes"]]),
    ], sheet_name="Source Sheet")
    result = _answer(summary, index,
                     "'Source Sheet'!B1, 'Source Sheet'!C1의 Orion 작업과 Vega 작업은 같은 항목이야?", 1)
    assert result is None or (result.status == "insufficient_evidence" and result.verification.level == "unverified")


def test_exact_header_range_disambiguates_repeated_header_names_across_tables():
    summary, index = table_fixture([
        (1, 1, [["Record", "Orion 작업", "Vega 작업"], ["R1", "yes", "no"]]),
        (7, 5, [["Record", "Orion 작업", "Vega 작업"], ["R2", "no", "yes"]]),
    ], sheet_name="Source Sheet")
    result = _answer(summary, index,
                     "'Source Sheet'!F7:G7의 Orion 작업과 Vega 작업은 같은 항목이야?", 1)
    assert result.status == "limited", result.answer
    assert result.verification.level == "source_checked"
    assert {item.reference for item in result.evidence} == {"F7", "G7"}
