from dataclasses import replace

import pytest

from app.agent.query.relational_execution import relational_query_answer
from tests.relational_query_fixtures import answer, relational_fixture, relational_plan


def assert_blocked(result, reason):
    assert result.status == "insufficient_evidence", result.answer
    assert reason in result.answer
    assert result.verification.level == "unverified"


def test_duplicate_right_keys_do_not_multiply_a_sum():
    summary, index = relational_fixture(right=[["Customer ID", "Region"], ["C1", "North"], ["C1", "South"]])
    assert_blocked(answer(summary, index), "중복")


@pytest.mark.parametrize("key", ["#N/A", "#REF!", "#DIV/0!"])
def test_error_join_keys_are_not_usable_source_keys(key):
    summary, index = relational_fixture(left=[["Order ID", "Customer ID", "Amount"], ["ORD-1", key, 10], ["ORD-2", "C2", 20]])
    assert_blocked(answer(summary, index), "키")


@pytest.mark.parametrize("key", ["1", "01", True])
def test_key_coercion_does_not_conflate_text_number_boolean(key):
    summary, index = relational_fixture(
        left=[["Order ID", "Customer ID", "Amount"], ["ORD-1", key, 10], ["ORD-2", 2, 20]],
        right=[["Customer ID", "Region"], [1, "North"], [2, "South"]])
    assert_blocked(answer(summary, index, join_type="inner"), "찾지 못해")


def test_unmatched_outer_group_cannot_silently_disappear_from_total():
    summary, index = relational_fixture(right=[["Customer ID", "Region"], ["C1", "North"], ["C3", "West"]])
    result = answer(summary, index)
    assert result.status == "limited", result.answer
    assert "Region=North; Orders.Amount: 합계 10" in result.answer
    assert "Region=연결 안 됨 (그룹 미확정); Orders.Amount: 합계 20" in result.answer
    assert result.verification.level == "source_checked"
    assert any("그룹을 확정하지 못한 왼쪽 행 1개" in limitation for limitation in result.limitations)


def test_missing_amount_is_not_zero_or_excluded_from_total():
    summary, index = relational_fixture(left=[["Order ID", "Customer ID", "Amount"], ["ORD-1", "C1", None], ["ORD-2", "C2", 20]])
    assert_blocked(answer(summary, index), "누락값은 0")


def test_missing_formula_cache_never_becomes_zero():
    summary, index = relational_fixture(left=[["Order ID", "Customer ID", "Amount"], ["ORD-1", "C1", "=1+2"], ["ORD-2", "C2", 20]])
    assert_blocked(answer(summary, index), "수식 저장값")


def test_incomplete_region_or_index_is_not_full_population_proof():
    summary, index = relational_fixture()
    region = replace(summary.sheets[0].regions[0], analysis_complete=False)
    sheet = replace(summary.sheets[0], regions=[region])
    partial = replace(summary, sheets=[sheet, summary.sheets[1]])
    assert_blocked(answer(partial, index), "전체 행")
    cutoff = replace(index, rows=tuple(row for row in index.rows if row.row_number < 3), truncated=True)
    assert_blocked(answer(summary, cutoff), "전체 행")


def test_aggregating_right_values_repeated_by_detail_rows_is_blocked():
    summary, index = relational_fixture(
        left=[["Order ID", "Customer ID", "Amount"], ["ORD-1", "C1", 10], ["ORD-2", "C1", 20]],
        right=[["Customer ID", "Region", "Budget"], ["C1", "North", 100], ["C2", "South", 200]])
    result = answer(summary, index, "Orders와 Customers를 Customer ID로 연결해서 Budget 합계",
                    column_ids=["right.C"], group_by=[])
    assert_blocked(result, "중복 집계")


def test_unknown_table_or_column_is_rejected_without_fallback_guess():
    summary, index = relational_fixture()
    for changes in ({"left_table_id": "invented"}, {"column_ids": ["right.Missing"]}):
        plan = relational_plan(summary, **changes)
        assert_blocked(relational_query_answer(plan, summary, index, "합계"), "확정")
