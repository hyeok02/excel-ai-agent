"""Unbound scope cannot receive a matrix badge, regardless of model field style."""
from dataclasses import replace

import pytest

from app.agent.query.source_matrix_bindings import source_matrix_bindings
from tests.support.matrix_claim_fixtures import MATRIX, claim, response, setup
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("changes", [
    {"subject_reference": "planning!a11", "property_reference": "planning!b10", "period_reference": None},
    {"subject_reference": None, "property_reference": "Planning!A11", "period_reference": "Planning!B10"},
    {"subject_reference": "Planning!B10", "property_reference": "Planning!A11", "period_reference": None},
])
def test_both_live_provider_field_conventions_use_the_same_proven_axes(changes):
    _, _, _, execution = setup()
    result = response(execution, [claim(**changes)])
    assert result.status == "answered" and result.verification.level == "source_checked"
    assert "Revenue" in result.answer and "Latest period" in result.answer and "120.5" in result.answer


@pytest.mark.parametrize("question", [
    "What is OtherCorp Revenue for Latest period?",
    "Planning에서 Latest period의 Revenue 값은 얼마야? 다른 회사 기준으로",
    "Planning에서 Latest period의 Revenue 값은 얼마야? 미국만",
    "Planning에서 Latest period의 Revenue 값을 2배 해줘",
    "Planning에서 Latest period의 Revenue 중 제품 A만",
    "Why did OtherCorp Revenue increase in Latest period?",
])
@pytest.mark.parametrize("ordinary_shape", [False, True])
def test_unknown_entity_filter_or_arithmetic_never_receives_a_source_badge(question, ordinary_shape):
    _, _, _, execution = setup()
    changes = {"subject_reference": "Planning!A11", "property_reference": "Planning!B10",
               "period_reference": None} if ordinary_shape else {}
    result = response(execution, [claim(**changes)], question=question)
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"
    assert "120.5" not in result.answer


def test_a_sheet_name_cannot_supply_the_missing_metric_mention():
    _, _, _, execution = setup(sheet="Revenue")
    selected = {key: value.replace("Planning!", "Revenue!") if isinstance(value, str) else value
                for key, value in claim().items()}
    result = response(execution, [selected], question="Revenue에서 Latest period 값은?")
    assert result.verification.level == "unverified"
    result = response(execution, [selected], question="Revenue에서 Latest period의 Revenue 값은 얼마야?")
    assert result.status == "answered" and result.verification.level == "source_checked"


def test_metric_label_cannot_arbitrarily_select_an_identically_named_sheet():
    summary, index, cells, execution = setup(sheet="Revenue")
    other_summary, other_index = table_fixture([(10, 1, MATRIX)], "Other")
    summary.sheets.extend(other_summary.sheets)
    index = replace(index, rows=index.rows + other_index.rows,
                    indexed_cell_count=index.indexed_cell_count + other_index.indexed_cell_count)
    execution.steps[0].result.data["source_matrix_bindings"] = source_matrix_bindings(summary, index, cells)
    selected = {key: value.replace("Planning!", "Revenue!") if isinstance(value, str) else value
                for key, value in claim().items()}
    result = response(execution, [selected], question="Latest period의 Revenue 값은 얼마야?")
    assert result.verification.level == "unverified"
    result = response(execution, [selected], question="Revenue에서 Latest period의 Revenue 값은 얼마야?")
    assert result.status == "answered"


def test_proven_matrix_evidence_replaces_wrong_region_descriptions_without_changing_sources():
    _, _, _, execution = setup()
    source = execution.steps[0].result
    source.evidence = [item.model_copy(update={"description": "Unrelated country / domicile"})
                       for item in source.evidence]
    original = {item.reference: item.model_dump() for item in source.evidence}
    result = response(execution)
    assert result.status == "answered" and result.verification.level == "source_checked"
    expected = {"A11": "교차표 행 항목: Revenue", "B10": "교차표 열 항목: Latest period",
                "B11": "교차표 원본 값: Revenue / Latest period"}
    assert {item.reference: item.description for item in result.evidence} == expected
    for item in result.evidence:
        assert item.label == f"원본 값: {item.value}"
        unchanged = item.model_dump(exclude={"description", "label"})
        assert unchanged == {key: value for key, value in original[item.reference].items() if key != "description"}
    assert all(item.description == "Unrelated country / domicile" for item in source.evidence)
