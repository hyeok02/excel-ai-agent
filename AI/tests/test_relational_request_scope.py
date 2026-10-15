import pytest

from tests.relational_query_fixtures import answer, relational_fixture
from tests.test_relational_safety import assert_blocked


def test_unrequested_matched_only_population_is_rejected():
    summary, index = relational_fixture()
    assert_blocked(answer(summary, index, population="matched_only"), "임의로 제외")


def test_wrong_statistic_cannot_receive_a_verified_label():
    summary, index = relational_fixture()
    assert_blocked(answer(summary, index, statistic="average"), "집계 방식")


def test_wrong_column_is_rejected_even_when_every_source_value_is_real():
    summary, index = relational_fixture(left=[["Order ID", "Customer ID", "Amount", "Tax"],
                                             ["ORD-1", "C1", 10, 1], ["ORD-2", "C2", 20, 2]])
    assert_blocked(answer(summary, index, column_ids=["left.D"]), "Amount")


def test_missing_grouping_cannot_be_replaced_by_whole_table_total():
    summary, index = relational_fixture()
    assert_blocked(answer(summary, index, group_by=[]), "Region")


def test_unrequested_grouping_is_not_an_answer_about_a_grand_total():
    summary, index = relational_fixture()
    assert_blocked(answer(summary, index, "Orders와 Customers를 Customer ID로 연결한 Amount 합계"), "그룹 기준")


def test_join_key_is_not_automatically_an_additional_grouping_dimension():
    summary, index = relational_fixture()
    assert_blocked(answer(summary, index, group_by=["right.B", "left.B"]), "그룹 기준")


def test_unrequested_filter_cannot_remove_valid_source_rows():
    summary, index = relational_fixture()
    assert_blocked(answer(summary, index, filters=[{
        "side": "left", "column_id": "A", "operator": "equals", "value": "ORD-1",
    }]), "조건")


def test_requested_filter_must_not_be_omitted():
    summary, index = relational_fixture()
    assert_blocked(answer(summary, index, "Orders와 Customers를 Customer ID로 연결해서 ORD-1의 Amount 합계",
                          group_by=[]), "조건")


def test_right_filter_cannot_silently_change_all_left_population():
    summary, index = relational_fixture()
    assert_blocked(answer(summary, index, "Orders와 Customers를 Customer ID로 연결해서 Region이 North인 Amount 합계",
                          group_by=[], filters=[{"side": "right", "column_id": "B", "operator": "equals", "value": "North"}]),
                   "보존할지")


def test_explicit_right_filter_matched_population_is_executable():
    summary, index = relational_fixture()
    result = answer(summary, index,
                    "Orders와 Customers를 Customer ID로 연결해서 Region이 North인 매칭된 행의 Amount 합계",
                    group_by=[], population="matched_only", join_type="inner",
                    filters=[{"side": "right", "column_id": "B", "operator": "equals", "value": "North"}])
    assert result.status == "limited", result.answer
    assert "합계 10" in result.answer
    assert result.verification.level != "request_checked"


def test_partial_explicit_range_is_not_answered_by_whole_table_sum():
    summary, index = relational_fixture()
    assert_blocked(answer(summary, index, "'Orders'!A1:C2와 Customers를 연결한 Amount 합계", group_by=[]), "부분 셀")


def test_nonmatching_key_names_require_explicit_mapping():
    summary, index = relational_fixture(right=[["Account ID", "Region"], ["C1", "North"], ["C2", "South"]])
    assert_blocked(answer(summary, index), "대응 관계")
    result = answer(summary, index, "Orders의 Customer ID와 Customers의 Account ID를 연결해서 Region별 Amount 합계")
    assert result.status == "answered", result.answer


@pytest.mark.parametrize("operation", ["lookup", "row_list"])
def test_aggregate_request_cannot_be_replaced_by_plain_projection(operation):
    summary, index = relational_fixture()
    assert_blocked(answer(summary, index, operation=operation), "집계")
