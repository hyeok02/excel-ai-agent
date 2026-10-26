"""Exact categorical counts survive missing planners without heuristic counts."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.source_count_answers import checked_legacy_count, source_count_answer
from tests.support.large_workbook_fixtures import offline, NoGeneratedAnswer
from tests.tabular_query_fixtures import table_fixture


def source(reverse=False, second=False):
    rows = [["A", "ready", "Q"], ["B", "ready", "Q"], ["C", "pending", "P"]]
    if reverse:
        rows.reverse()
    blocks = [(8, 3, [["Ticket", "Review State", "Flag"], *rows])]
    if second:
        blocks.append((20, 3, [["Ticket", "Review State", "Flag"], ["D", "ready", "Q"]]))
    return table_fixture(blocks, sheet_name="Requests")


@pytest.mark.parametrize("question,expected", [
    ("Requests 시트에서 Review State가 ready인 요청은 몇 건이야?", 2),
    ("Review State가 ready인 행 개수 알려줘", 2),
    ("How many records where Review State is ready?", 2),
    ("Review State가 ready가 아닌 행은 몇 건이야?", 1),
    ("Review State가 missing인 요청은 몇 건이야?", 0),
])
@pytest.mark.parametrize("reverse", [False, True])
def test_source_counts_use_complete_table_and_filter_before_any_model(question, expected, reverse):
    summary, index = source(reverse)
    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry())
    result = asyncio.run(service.answer(question, summary, index))
    assert result.status == "answered" and f"{expected}건" in result.answer
    assert result.verification.level == "request_checked"
    assert "D8:D11" in {cell.reference for cell in result.evidence}


@pytest.mark.parametrize("question", [
    "Review State가 ready 또는 pending인 요청은 몇 건이야?",
    "Review State가 ready인 요청 중 Amount가 100 이상인 건수",
    "Review State가 ready인 요청 수를 예측해줘",
    "Review State가 ready인 요청 중 최근1년 건수",
    "2024년 Review State가 ready인 요청은 몇 건이야?",
    "Review State가 ready인 요청 중 서울 건수",
    "Review State가 ready인 요청 중 미완료 건수",
])
def test_unbound_extra_conditions_are_not_dropped(question):
    summary, index = source()
    assert source_count_answer(question, summary, index) is None


def test_two_complete_tables_do_not_choose_the_first_matching_filter():
    summary, index = source(second=True)
    assert source_count_answer("Review State가 ready인 행은 몇 건이야?", summary, index) is None


def test_legacy_counter_cannot_promote_a_data_cell_to_a_column_header():
    summary, index = source()
    found = {"header_reference": "Requests!D9", "header": "ready", "count": 3}
    assert checked_legacy_count("Review State가 ready인 행은 몇 건이야?", found, summary, index) is None


def test_legacy_total_cannot_drop_a_categorical_filter():
    summary, index = source()
    found = {"header_reference": "Requests!C8", "header": "Ticket", "count": 3}
    assert checked_legacy_count("Review State가 ready인 Ticket은 몇 건이야?", found, summary, index) is None


def test_literal_internal_spaces_do_not_change_the_requested_value():
    summary, index = table_fixture([(1, 1, [["Record", "Category"],
        ["A", "alpha  beta"], ["B", "alpha beta"], ["C", "alpha  beta"]])])
    result = source_count_answer('Category가 "alpha  beta"인 행은 몇 건이야?', summary, index)
    assert result is not None and "2건" in result.answer
