import asyncio
from dataclasses import replace

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.question_formula_sources import prepare_formula_sources
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.source_lookup_answers import source_lookup_answer
from app.agent.query.workbook_source import WorkbookSource
from app.agent.query.workbook_source_models import SourceReadLimits
from tests.support.large_workbook_fixtures import offline, parsed, tiny_caps, workbook


class NoModel:
    async def classify(self, *args):
        raise AssertionError("Direct source reads must precede classification")

    async def generate(self, *args):
        raise AssertionError("Direct source reads cannot use generated answers")


def ask(question, summary, index):
    service = WorkbookQuestionService(NoModel(), create_default_tool_registry(), classifier=NoModel())
    return asyncio.run(service.answer(question, summary, index))


def fixture(limits=None):
    return parsed(workbook({"Records": [["ID", "Amount"], *[[f"R{i}", i * 10] for i in range(1, 11)]]}), limits=limits)


def test_tail_cell_and_small_range_are_reread_without_claiming_whole_index_complete(tiny_caps):
    summary, index, _ = fixture()
    assert index.truncated and all(row.row_number < 5 for row in index.rows)
    response = ask("Records!B10:B11 값을 보여줘", summary, index)
    assert "Records!B10: 90" in response.answer and "Records!B11: 100" in response.answer
    assert response.verification.level == "request_checked" and response.status == "answered"
    assert "complete_source_read" in response.verification.checks
    assert {item.reference for item in response.evidence} == {"B10", "B11"}
    assert index.truncated and all(row.row_number < 5 for row in index.rows)


def test_later_sheet_missing_from_global_index_is_still_directly_addressable(tiny_caps):
    book = workbook({"Front": [["ID", "Amount"], *[[f"R{i}", i] for i in range(20)]],
                     "O'Brien": [["ID", "Amount"], ["TAIL", 731]]})
    summary, index, _ = parsed(book)
    # Force the same absent-sheet shape produced by the global cell budget.
    index = replace(index, rows=tuple(row for row in index.rows if row.sheet_name == "Front"))
    response = ask("'O''Brien'!$B$2의 값은?", summary, index)
    assert "731" in response.answer and response.verification.level == "request_checked"
    assert response.evidence[0].sheet_name == "O'Brien"


def test_confirmed_blank_boolean_and_percentage_are_not_confused(tiny_caps):
    book = workbook({"Records": [["ID", "Amount"], ["a", 1], ["b", 2], ["c", False], ["d", .25]]})
    book["Records"]["B5"].number_format = "0%"
    summary, index, _ = parsed(book)
    response = ask("Records!B4:B5, Records!C5 값", summary, index)
    assert "FALSE" in response.answer and "25%" in response.answer and "빈 셀" in response.answer
    assert response.verification.level == "request_checked"


def test_uncached_tail_formula_never_becomes_a_verified_zero(tiny_caps):
    book = workbook({"Records": [["ID", "Amount"], ["a", 1], ["b", 2], ["c", '=IFERROR(_xll.Remote(),0)']]})
    summary, index, _ = parsed(book)
    response = ask("Records!B4 값은?", summary, index)
    assert response.status == "insufficient_evidence" and response.verification.level == "unverified"
    assert response.evidence[0].formula == '=IFERROR(_xll.Remote(),0)'
    assert response.evidence[0].value is None


@pytest.mark.parametrize("question", [
    "Records!B10의 합계는?", "Records!B10을 EUR로 변환해줘", "Records!B10 값이 왜 높아?",
    "Records!B10과 Records!B11 차이", "Records!B10:B11 중 95 이상 값", "Records!B10이 100인지 확인",
    "Records!B10 값에 2 곱해줘", "Records!B10 excluding R9", "Records!B10은 원본과 같은가?",
])
def test_direct_lookup_does_not_silently_ignore_operations_units_or_conditions(tiny_caps, question):
    summary, index, _ = fixture()
    assert source_lookup_answer(question, prepare_formula_sources(summary, index)) is None


@pytest.mark.parametrize("question", ["Other!B10 값", "Records!B0 값", "Records!B11:B10 값", "Records!A1:C100 값"])
def test_unknown_invalid_or_oversized_scope_is_not_verified(tiny_caps, question):
    summary, index, _ = fixture()
    response = ask(question, summary, index)
    assert response.status == "insufficient_evidence" and response.verification.level == "unverified"


def test_wrong_workbook_digest_is_rejected_before_source_access(tiny_caps):
    summary, index, _ = fixture()
    response = ask("Records!B10 값", summary, replace(index, source_digest="0" * 64))
    assert response.status == "insufficient_evidence" and not response.evidence


@pytest.mark.parametrize("limits", [SourceReadLimits(max_rows=1), SourceReadLimits(max_seconds=0)])
def test_budget_failure_does_not_turn_unread_cells_into_blank(tiny_caps, limits):
    summary, index, _ = fixture(limits)
    response = ask("Records!B10:B11 값", summary, index)
    assert response.status == "insufficient_evidence" and not response.evidence
    assert "빈 셀" not in response.answer


def test_incomplete_scan_cannot_certify_its_partial_rows(tiny_caps, monkeypatch):
    summary, index, _ = fixture()
    class Incomplete:
        complete = False
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def __iter__(self): return iter(index.rows[:1])
    monkeypatch.setattr(WorkbookSource, "scan_rows", lambda *args: Incomplete())
    response = ask("Records!B10 값", summary, index)
    assert response.status == "insufficient_evidence" and not response.evidence


def test_small_existing_recoverable_formula_keeps_derived_verification():
    summary, index, _ = parsed(workbook({"Records": [["ID", "Amount"], ["a", "=1+2"]]}))
    response = ask("Records!B2 값", summary, index)
    assert "3" in response.answer and response.verification.level == "source_checked"
    assert response.status == "limited" and "bounded_recalculation" in response.verification.checks


def test_explicit_hidden_row_column_read_matches_existing_authorized_sheet_policy(tiny_caps):
    book = workbook({"Records": [["ID", "Amount"], *[[f"R{i}", i * 10] for i in range(1, 11)]]})
    book["Records"].row_dimensions[10].hidden = True
    book["Records"].column_dimensions["B"].hidden = True
    summary, index, _ = parsed(book)
    response = ask("Records!B10 값", summary, index)
    assert "90" in response.answer and response.verification.level == "request_checked"


def test_truncated_display_is_disclosed_and_never_gets_request_checked():
    summary, index, _ = parsed(workbook({"Records": [["ID", "Text"], ["a", "x" * 1000]]}))
    response = ask("Records!B2 값", summary, index)
    assert response.status == "limited" and response.verification.level == "source_checked"
    assert len(response.evidence[0].value) == 500
    assert response.limitations and "500" in response.limitations[0]
