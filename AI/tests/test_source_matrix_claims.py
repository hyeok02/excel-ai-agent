"""Actual matrix axes can prove a lookup; proximity or model text cannot."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from app.agent.execution import AgentStepStatus
from app.agent.query.source_matrix_bindings import source_matrix_bindings
from tests.tabular_query_fixtures import table_fixture
from tests.support.matrix_claim_fixtures import MATRIX, claim, response, setup


def test_numeric_matrix_lookup_is_answered_from_original_axes_without_a_false_limit():
    _, _, _, execution = setup()
    result = response(execution)
    assert result.status == "answered"
    assert result.verification.level == "source_checked"
    assert "120.5" in result.answer and "Revenue" in result.answer and "Latest period" in result.answer
    assert "교차점" in result.answer
    assert not result.limitations
    assert "unsupported" not in result.answer


@pytest.mark.parametrize("changes", [
    {"property_reference": "Planning!A12"}, {"period_reference": "Planning!C10"},
    {"value_reference": "Planning!C11"}, {"subject_reference": "Planning!A12"},
    {"period_reference": None, "subject_reference": None}, {"fact": "Revenue grew because of sales"},
])
def test_wrong_row_period_property_or_subject_is_not_verified(changes):
    _, _, _, execution = setup()
    result = response(execution, [claim(**changes)])
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified"


def test_conflicting_authoritative_column_binding_is_not_overridden():
    _, _, _, execution = setup()
    execution.steps[0].result.data["source_header_bindings"] = {"planning!b11": "planning!c10"}
    assert response(execution).verification.level == "unverified"


def test_conflicting_matrix_proofs_are_not_arbitrarily_selected():
    _, _, _, execution = setup()
    step = execution.steps[0]
    proof = {**step.result.data["source_matrix_bindings"]["planning!b11"], "column_reference": "planning!c10"}
    execution.steps.append(SimpleNamespace(status=AgentStepStatus.SUCCEEDED, tool_name=step.tool_name,
        result=SimpleNamespace(evidence=step.result.evidence, data={"source_matrix_bindings": {"planning!b11": proof}})))
    assert response(execution).verification.level == "unverified"


def test_three_adjacent_cells_without_a_rectangle_do_not_establish_matrix_axes():
    _, _, _, execution = setup([(10, 1, MATRIX[:2])])
    assert not execution.steps[0].result.data["source_matrix_bindings"]
    assert response(execution).verification.level == "unverified"


def test_text_record_above_numbers_is_not_promoted_to_matrix_headers():
    block = [["Is active?", "Yes", "Check source"], ["Revenue", 120, 100], ["Costs", 60, 50]]
    _, _, _, execution = setup([(10, 1, block)])
    assert not execution.steps[0].result.data["source_matrix_bindings"]


def test_duplicate_matching_matrices_require_an_explicit_source_selector():
    _, _, _, execution = setup([(10, 1, MATRIX), (20, 1, MATRIX)])
    assert response(execution).verification.level == "unverified"
    result = response(execution, question="Planning!B11 값은?")
    assert result.verification.level == "source_checked"
    assert "120.5" in result.answer


def test_unretrieved_matching_matrix_on_another_sheet_is_not_ignored():
    summary, index, cells, execution = setup()
    other_summary, other_index = table_fixture([(10, 1, MATRIX)], "Other")
    summary.sheets.extend(other_summary.sheets)
    index = replace(index, rows=index.rows + other_index.rows,
                    indexed_cell_count=index.indexed_cell_count + other_index.indexed_cell_count)
    # Other's cells are deliberately absent from the current search evidence.
    execution.steps[0].result.data["source_matrix_bindings"] = source_matrix_bindings(summary, index, cells)
    assert response(execution, question="Latest period의 Revenue 값은 얼마야?").verification.level == "unverified"
    assert response(execution).status == "answered"
    assert response(execution, question="Other에서 Latest period의 Revenue 값은 얼마야?").verification.level == "unverified"


def test_incomplete_other_sheet_requires_an_explicit_complete_sheet_selector():
    summary, index, cells, execution = setup()
    other_summary, _ = table_fixture([(10, 1, MATRIX)], "Other")
    summary.sheets.extend(other_summary.sheets)
    index = replace(index, truncated=True, truncated_sheet_names=frozenset({"Other"}))
    execution.steps[0].result.data["source_matrix_bindings"] = source_matrix_bindings(summary, index, cells)
    assert response(execution, question="Latest period의 Revenue 값은 얼마야?").verification.level == "unverified"
    assert response(execution).status == "answered"


def test_value_and_axes_must_match_current_index_and_be_in_tool_evidence():
    summary, index, cells, _ = setup()
    changed = [replace(cell, value=999) if cell.reference == "B11" else cell for cell in cells]
    assert "planning!b11" not in source_matrix_bindings(summary, index, changed)
    without_axis = [cell for cell in cells if cell.reference != "A11"]
    assert "planning!b11" not in source_matrix_bindings(summary, index, without_axis)


def test_truncated_or_merged_layouts_cannot_create_structural_proofs():
    summary, index, cells, _ = setup()
    assert source_matrix_bindings(summary, replace(index, truncated=True), cells) == {}
    region = summary.sheets[0].regions[0]
    region.merged_ranges.append("B10:C10")
    assert source_matrix_bindings(summary, index, cells) == {}


@pytest.mark.parametrize("question", [
    "Planning에서 Latest period의 Revenue가 증가한 이유는?",
    "Planning에서 Latest period의 Revenue 값이 정상인지 설명해줘",
])
def test_matrix_value_does_not_validate_cause_or_business_interpretation(question):
    _, _, _, execution = setup()
    result = response(execution, question=question)
    assert result.status == "limited"
    assert "정상" not in result.answer and "이유" not in result.answer
    assert result.limitations


@pytest.mark.parametrize("question", [
    "Planning에서 Prior period의 Revenue 값은 얼마야?",
    "Planning에서 Latest period의 Operating costs 값은 얼마야?",
    "Planning에서 Latest period의 Revenue가 200 이상인 값은?",
])
def test_selected_matrix_still_obeys_question_metric_period_and_conditions(question):
    _, _, _, execution = setup()
    assert response(execution, question=question).verification.level == "unverified"


def test_unknown_or_invalid_claims_keep_the_response_limited():
    _, _, _, execution = setup()
    result = response(execution, [claim(), {"kind": "unknown"}])
    assert result.status == "limited" and result.verification.level == "source_checked"
    assert "120.5" in result.answer
