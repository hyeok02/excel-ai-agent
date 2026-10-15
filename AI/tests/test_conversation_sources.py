"""Conversation hints must be rebound to this request's visible workbook cells."""
from io import BytesIO
from dataclasses import replace

import pytest
from openpyxl import Workbook

from app.agent.query.conversation_checks import resolution_is_safe
from app.agent.query.conversation_models import ContextResolutionDraft, QuestionConversation
from app.agent.query.conversation_sources import source_bound_context
from app.agent.query.index import build_workbook_data_index
from app.agent.query.tabular_catalog import build_query_tables
from app.services.workbook_parser import parse_workbook


def conversation_fixture(sheet_name="Sales", include_hidden=False):
    book = Workbook()
    sheet = book.active
    sheet.title = sheet_name
    sheet.append(["Item", "January", "February"])
    sheet.append(["Notebook", 10, 20])
    sheet.append(["Monitor", 30, 40])
    hidden = book.create_sheet("Hidden")
    hidden.append(["Private metric", "SECRET SOURCE"])
    hidden.sheet_state = "hidden"
    output = BytesIO()
    book.save(output)
    book.close()
    content = output.getvalue()
    summary = parse_workbook("current.xlsx", content, include_hidden)
    index = build_workbook_data_index("current.xlsx", content, {sheet.name for sheet in summary.sheets})
    return content, summary, index


def _conversation(reference, question="Notebook의 January 값은?"):
    return QuestionConversation.model_validate({"turns": [{"question": question, "evidence": [reference]}]})


@pytest.mark.parametrize("reference", [
    "Other!A1", "Sales!Z999", "A1", "https://invalid.example/secret", "[other.xlsx]Sales!A1",
    "Sales!A1:XFD1048576", "Sales!A0", "Sales!invalid",
])
def test_missing_external_or_unbounded_references_do_not_supply_context(reference):
    _, summary, index = conversation_fixture()
    assert source_bound_context(_conversation(reference), summary, index) == []


@pytest.mark.parametrize("include_hidden", [False, True])
def test_hidden_sheet_hints_follow_authorized_parser_scope(include_hidden):
    _, summary, index = conversation_fixture(include_hidden=include_hidden)
    entries = source_bound_context(_conversation("Hidden!A1:B1"), summary, index)
    assert bool(entries) is include_hidden
    if include_hidden:
        assert "SECRET SOURCE" in str(entries[0]["source_cells"])


def test_quoted_apostrophe_sheet_reference_rereads_current_cells_and_headers():
    _, summary, index = conversation_fixture("O'Brien Data")
    entries = source_bound_context(_conversation("'O''Brien Data'!$B$2"), summary, index)
    assert len(entries) == 1
    values = {cell["reference"]: cell["value"] for cell in entries[0]["source_cells"]}
    assert values["O'Brien Data!B2"] == 10
    assert "January" in values.values()


def test_previous_question_numbers_are_hints_not_current_source_values():
    _, summary, index = conversation_fixture()
    entries = source_bound_context(_conversation("Sales!B2", "Notebook는 999999야?"), summary, index)
    assert entries[0]["hint"]["question"] == "Notebook는 999999야?"
    assert 999999 not in [cell["value"] for cell in entries[0]["source_cells"]]
    assert 10 in [cell["value"] for cell in entries[0]["source_cells"]]


def test_value_only_previous_citation_includes_original_row_entity_for_followups():
    _, summary, index = conversation_fixture()
    entries = source_bound_context(_conversation("Sales!B2"), summary, index)
    values = [cell["value"] for cell in entries[0]["source_cells"]]
    assert "January" in values
    assert "Notebook" in values


def test_invalid_entries_are_dropped_without_renumbering_recency_ids():
    _, summary, index = conversation_fixture()
    context = QuestionConversation.model_validate({"turns": [
        {"question": "첫 질문", "evidence": ["Sales!B2"]},
        {"question": "다른 파일", "evidence": ["Other!A1"]},
        {"question": "마지막 질문", "evidence": ["Sales!C2"]},
    ], "insights": [{"title": "월별 수치", "topic": None, "evidence": ["Sales!A1:C3"]}]})
    entries = source_bound_context(context, summary, index)
    assert [entry["id"] for entry in entries] == ["turn:2", "turn:0", "insight:0"]
    assert all(len(entry["source_cells"]) <= 24 for entry in entries)


@pytest.mark.parametrize("original,rewritten", [
    ("그중 #42 값은?", "Sales!B2의 Notebook 값은?"),
    ("그중 #42 값은?", "Notebook 중 #420 값은?"),
    ("그중 #42 값은?", "Notebook 중 42개 값은?"),
    ("그중 AX42 값은?", "Notebook 중 AX43 값은?"),
    ("그중 East 값은?", "Notebook 중 West 값은?"),
    ("그중 3 미만은?", "Notebook 중 3 초과는?"),
    ("그중 3 이상은?", "Notebook 중 30 이상은?"),
    ("그중 100 이상은?", "Notebook 중 1000 이상은?"),
    ("그중 20% 이상은?", "Notebook 중 200% 이상은?"),
    ("그중 20% 이상은?", "Notebook 중 20 이상은?"),
    ("그중 2025년 합계는?", "Notebook의 2026년 합계는?"),
    ("그중 아닌 항목은?", "Notebook 항목은?"),
    ("그중 평균은?", "Notebook의 합계는?"),
    ("그중 'Monitor' 값은?", "Notebook 값은?"),
    ("그중 Sales!B2 값은?", "Notebook의 Sales!C2 값은?"),
])
def test_rewrites_must_not_drop_or_change_explicit_constraints(original, rewritten):
    _, summary, index = conversation_fixture()
    entries = source_bound_context(_conversation("Sales!A1:C3"), summary, index)
    draft = ContextResolutionDraft(status="resolved", question=rewritten, context_ids=["turn:0"])
    assert not resolution_is_safe(original, draft, entries)


def test_rewrite_keeps_explicit_numbers_negation_scope_and_source_label():
    _, summary, index = conversation_fixture()
    entries = source_bound_context(_conversation("Sales!A1:C3"), summary, index)
    draft = ContextResolutionDraft(status="resolved", question="Notebook 중 #42 제외하고 20 이상 합계는?",
                                   context_ids=["turn:0"])
    assert resolution_is_safe("그중 #42 제외하고 20 이상 합계는?", draft, entries)
    assert not resolution_is_safe("그중 합계는?", draft.model_copy(update={"context_ids": ["turn:9"]}), entries)


def test_large_table_membership_keeps_headers_without_expanding_oversized_citation(monkeypatch):
    _, summary, index = conversation_fixture()
    table = replace(build_query_tables(summary)[0], id="Sales!A1:C10000", reference="A1:C10000")
    monkeypatch.setattr("app.agent.query.conversation_sources.build_query_tables", lambda _summary: [table])
    entries = source_bound_context(_conversation("Sales!B2"), summary, index)
    values = [cell["value"] for cell in entries[0]["source_cells"]]
    assert "January" in values and "Notebook" in values
    assert source_bound_context(_conversation(table.id), summary, index) == []
