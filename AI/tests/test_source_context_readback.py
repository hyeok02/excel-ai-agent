import asyncio
from dataclasses import replace

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.conversation_models import ContextResolutionDraft, QuestionConversation
from app.agent.query.conversation_sources import source_bound_context
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.workbook_source_models import SourceReadLimits
from tests.support.large_workbook_fixtures import offline, parsed, tiny_caps, workbook
from tests.test_source_lookup_answers import NoModel


def fixture(limits=None):
    return parsed(workbook({"Records": [["ID", "Amount"], *[[f"R{i}", i * 10] for i in range(1, 11)]]}), limits=limits)


def context(reference="Records!B10"):
    return QuestionConversation(turns=[{"question": "Records!B10 값은?", "evidence": [reference]}])


class Resolver:
    def __init__(self, resolved):
        self.resolved, self.seen = resolved, None

    async def resolve(self, question, entries):
        self.seen = entries
        return ContextResolutionDraft(status="resolved", question=self.resolved, context_ids=["turn:0"])


def test_tail_context_restores_current_value_header_and_row_identity(tiny_caps):
    summary, index, _ = fixture()
    entries = source_bound_context(context(), summary, index)
    assert len(entries) == 1
    cells = {cell["reference"]: cell["value"] for cell in entries[0]["source_cells"]}
    assert cells["Records!B10"] == 90 and cells["Records!A10"] == "R9"
    assert cells["Records!B1"] == "Amount"
    assert len(cells) <= 24 and index.truncated
    assert not any(row.row_number == 10 for row in index.rows)


def test_tail_followup_service_uses_original_source_and_downgrades_context_inference(tiny_caps):
    summary, index, _ = fixture()
    resolver = Resolver("Records!B10 값은?")
    service = WorkbookQuestionService(NoModel(), create_default_tool_registry(),
                                      classifier=NoModel(), context_resolver=resolver)
    response = asyncio.run(service.answer("그 값은?", summary, index, context()))
    assert "90" in response.answer and response.resolved_question == resolver.resolved
    assert response.status == "limited" and response.verification.level == "source_checked"
    assert "context_resolved" in response.verification.checks
    assert resolver.seen[0]["source_cells"]


def test_later_sheet_context_does_not_require_any_original_index_rows(tiny_caps):
    book = workbook({"Front": [["ID", "Amount"], ["a", 1]],
                     "Later": [["ID", "Amount"], ["Tail", 731]]})
    summary, index, _ = parsed(book)
    index = replace(index, rows=tuple(row for row in index.rows if row.sheet_name == "Front"))
    entries = source_bound_context(context("Later!B2"), summary, index)
    assert any(cell["value"] == 731 for cell in entries[0]["source_cells"])
    assert any(cell["value"] == "Tail" for cell in entries[0]["source_cells"])


@pytest.mark.parametrize("reference", [
    "Other!B10", "Records!B0", "Records!B11:B10", "Records!A1:XFD1048576",
    "[remote.xlsx]Records!B10", "https://invalid.example/B10", "Records!Z999",
])
def test_invalid_external_excluded_or_blank_citations_do_not_create_context(tiny_caps, reference):
    summary, index, _ = fixture()
    assert source_bound_context(context(reference), summary, index) == []


def test_failed_tail_read_cannot_silently_reconnect_to_an_older_turn(tiny_caps):
    summary, index, _ = fixture(SourceReadLimits(max_seconds=0))
    conversation = QuestionConversation(turns=[
        {"question": "Records!B2 값?", "evidence": ["Records!B2"]},
        {"question": "Records!B10 값?", "evidence": ["Records!B10"]},
    ])
    resolver = Resolver("Records!B2 값?")
    service = WorkbookQuestionService(NoModel(), create_default_tool_registry(),
                                      classifier=NoModel(), context_resolver=resolver)
    response = asyncio.run(service.answer("그 값은?", summary, index, conversation))
    assert response.status == "insufficient_evidence" and response.verification.level == "unverified"
    assert not response.evidence


def test_same_filename_different_source_digest_cannot_supply_context(tiny_caps):
    summary, index, _ = fixture()
    other_book = workbook({"Records": [["ID", "Amount"], ["other", 999999]]})
    _, other_index, _ = parsed(other_book)
    mixed = replace(index, source_provider=other_index.source_provider)
    assert source_bound_context(context(), summary, mixed) == []


def test_large_reference_request_stays_bounded_and_does_not_expand_entire_sheet(tiny_caps):
    summary, index, _ = fixture()
    source_bound_context(context("Records!A1:C10000"), summary, index)
    assert index.source_provider._budget.reads == 0


def test_current_file_values_override_untrusted_previous_question_numbers(tiny_caps):
    summary, index, _ = fixture()
    conversation = QuestionConversation(turns=[{"question": "Records!B10 값은 999999야?", "evidence": ["Records!B10"]}])
    entries = source_bound_context(conversation, summary, index)
    assert 999999 not in [cell["value"] for cell in entries[0]["source_cells"]]
    assert 90 in [cell["value"] for cell in entries[0]["source_cells"]]
