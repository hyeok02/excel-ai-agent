"""Population-aware joins preserve coverage without fabricating relationships."""
import pytest

from tests.relational_query_fixtures import answer, relational_fixture
from tests.test_relational_safety import assert_blocked


@pytest.mark.parametrize("key", [None, "", "  "])
def test_blank_keys_on_both_sides_never_match_or_drop_left_rows(key):
    summary, index = relational_fixture(
        left=[["Order ID", "Customer ID", "Amount"], ["ORD-1", key, 10], ["ORD-2", "C2", 20]],
        right=[["Customer ID", "Region"], [key, "FalseMatch"], ["C2", "South"]])
    result = answer(summary, index)
    assert result.status == "limited", result.answer
    assert "연결 안 됨 1개" in result.answer and "그룹 미확정" in result.answer
    assert "FalseMatch" not in result.answer and "합계 10" in result.answer and "합계 20" in result.answer
    assert result.verification.level == "source_checked"
    assert any(item.sheet_name == "Orders" and item.reference == "C2" and item.value == 10 for item in result.evidence)


def test_filtered_lookup_is_not_blocked_by_unrelated_duplicate_dimension_keys():
    summary, index = relational_fixture(right=[["Customer ID", "Region"], ["C1", "North"],
                                               ["C2", "South"], ["C2", "Other"]])
    result = answer(summary, index, "Orders와 Customers를 Customer ID로 연결해서 ORD-1의 Region과 Amount",
                    operation="lookup", column_ids=["right.B", "left.C"], group_by=[],
                    filters=[{"side": "left", "column_id": "A", "operator": "equals", "value": "ORD-1"}])
    assert result.status == "answered", result.answer
    assert "North" in result.answer and "Other" not in result.answer
    assert result.verification.level == "source_checked"
    assert_blocked(answer(summary, index), "중복")


def test_blank_lookup_keys_cannot_block_unrelated_valid_matches():
    summary, index = relational_fixture(right=[["Customer ID", "Region"], ["C1", "North"],
                                               ["C2", "South"], [None, "Unknown"], ["", "Other"]])
    result = answer(summary, index)
    assert result.status == "answered", result.answer
    assert "합계 10" in result.answer and "합계 20" in result.answer
    assert "Unknown" not in result.answer and "Other" not in result.answer


def test_partially_empty_composite_keys_do_not_match():
    summary, index = relational_fixture(
        left=[["Record", "Customer ID", "Amount", "Period"], ["ORD-1", "C1", 10, None], ["ORD-2", "C1", 20, "Feb"]],
        right=[["Customer ID", "Region", "Period"], ["C1", "FalseMatch", None], ["C1", "South", "Feb"]])
    result = answer(summary, index, "Orders와 Customers를 Customer ID 및 Period로 연결해서 Region별 Amount 합계",
                    on=[{"left_column_id": "B", "right_column_id": "A"}, {"left_column_id": "D", "right_column_id": "C"}])
    assert result.status == "limited", result.answer
    assert "FalseMatch" not in result.answer and "연결 안 됨 1개" in result.answer
    assert "합계 10" in result.answer and "합계 20" in result.answer


def test_inner_join_still_cannot_silently_remove_blank_keys():
    summary, index = relational_fixture(left=[["Order ID", "Customer ID", "Amount"],
                                              ["ORD-1", None, 10], ["ORD-2", "C2", 20]])
    assert_blocked(answer(summary, index, join_type="inner"), "찾지 못해")


@pytest.mark.parametrize("names,offset", [(("Orders", "Customers"), (1, 1)), (("배송 내역", "소속 정보"), (8, 5))])
def test_unresolved_group_count_is_source_derived_after_renaming_and_moving(names, offset):
    summary, index = relational_fixture(right=[["Customer ID", "Region"], ["C1", "North"], ["C3", "West"]],
                                        names=names, offset=offset)
    result = answer(summary, index, f"{names[0]}와 {names[1]}를 Customer ID로 연결해서 Region별 건수",
                    operation="row_count", column_ids=[])
    assert result.status == "limited", result.answer
    assert "Region=North; 왼쪽 원본 행 기준 1건" in result.answer
    assert "Region=연결 안 됨 (그룹 미확정); 왼쪽 원본 행 기준 1건" in result.answer
    assert {item.sheet_name for item in result.evidence} == set(names)


def test_actual_blank_group_remains_distinct_from_failed_join():
    summary, index = relational_fixture(right=[["Customer ID", "Region", "Note"], ["C1", None, "kept"], ["C3", "West", "kept"]])
    result = answer(summary, index)
    assert result.status == "limited", result.answer
    assert "원본 그룹 값 비어 있음; Orders.Amount: 합계 10" in result.answer
    assert "연결 안 됨 (그룹 미확정); Orders.Amount: 합계 20" in result.answer
    assert any("왼쪽 행 2개" in item for item in result.limitations)


def test_unresolved_group_is_not_permission_to_treat_missing_amount_as_zero():
    summary, index = relational_fixture(
        left=[["Order ID", "Customer ID", "Amount"], ["ORD-1", "C1", 10], ["ORD-2", None, None]])
    assert_blocked(answer(summary, index), "누락값은 0")
