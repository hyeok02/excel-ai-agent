"""Whole-source scans enforce the same context contract after sampled rows."""
import pytest

from app.agent.query.tabular_execution import execute_tabular_query
from tests.support.large_workbook_fixtures import offline, parsed, plan_for, tiny_caps, workbook, equal


def source(last="EUR"):
    matrix = [["Record", "Amount", "Currency"], *[[f"Item{n}", n, "USD"] for n in range(1, 8)],
              ["Tail", 8, last]]
    return parsed(workbook({"Records": matrix}))[:2]


def test_tail_currency_after_sample_cannot_be_added_to_different_currency(tiny_caps):
    summary, index = source()
    result = execute_tabular_query(plan_for(summary), summary, index, "Records 시트 Amount 합계")
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"
    assert "통화·단위가 다른" in result.answer
    assert "합계 36" not in result.answer


def test_streaming_currency_filter_uses_full_population_and_source_control_evidence(tiny_caps):
    summary, index = source()
    result = execute_tabular_query(plan_for(summary, filters=[equal("C", "USD")]), summary, index,
                                   "Records 시트 Currency가 USD인 Amount 합계")
    assert result.status == "answered" and "합계 28" in result.answer
    assert result.verification.level == "request_checked" and "full_source_scan" in result.verification.checks
    assert "C1:C9" in {cell.reference for cell in result.evidence}


def test_streaming_separate_currency_groups_remain_valid(tiny_caps):
    summary, index = source()
    result = execute_tabular_query(plan_for(summary, group_by=["C"]), summary, index,
                                   "Records 시트 Currency별 Amount 합계")
    assert result.status == "answered"
    assert "합계 28" in result.answer and "합계 8" in result.answer
    assert "full_source_scan" in result.verification.checks


@pytest.mark.parametrize("last", ["USD", "U.S. Dollar"])
def test_uniform_currency_and_its_explicit_synonym_are_not_blocked(tiny_caps, last):
    summary, index = source(last)
    result = execute_tabular_query(plan_for(summary), summary, index, "Records 시트 Amount 합계")
    assert result.status == "answered" and "합계 36" in result.answer


def test_blank_amount_does_not_assign_or_conflict_with_numeric_unit():
    summary, index, _ = parsed(workbook({"Records": [["Record", "Amount", "Currency"],
        ["A", 10, "CAD"], ["B", None, None], ["C", 15, "CAD"]]}))
    result = execute_tabular_query(plan_for(summary), summary, index, "Records 시트 Amount 합계")
    assert result.status == "answered" and "합계 25" in result.answer and "빈칸 1건" in result.answer


def test_grouped_detail_filter_remains_valid_with_excluded_subtotal():
    matrix = [["Record", "Amount", "Department", "Row Role"], ["A", 10, "North", "Detail"],
              ["B", 20, "North", "Detail"], ["North total", 30, "North", "Subtotal"]]
    book = workbook({"Records": matrix})
    book.active.tables.clear()
    summary, index, _ = parsed(book)
    plan = plan_for(summary, group_by=["C"], filters=[equal("D", "Detail")])
    result = execute_tabular_query(plan, summary, index,
                                   "Records 시트 Row Role이 Detail인 Department별 Amount 합계")
    assert result.status == "answered" and "합계 30" in result.answer and "합계 60" not in result.answer
