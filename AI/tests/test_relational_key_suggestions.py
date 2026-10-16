"""Ambiguous joins ask about actual source keys instead of guessing a relationship."""
from tests.relational_query_fixtures import answer, relational_fixture
from tests.test_relational_safety import assert_blocked


def test_duplicate_dimension_ids_offer_an_observed_unique_extra_key_without_applying_it():
    summary, index = relational_fixture(
        left=[["Record", "Customer ID", "Amount", "Period"], ["ORD-1", "C1", 10, "Jan"], ["ORD-2", "C1", 20, "Feb"]],
        right=[["Customer ID", "Region", "Period"], ["C1", "North", "Jan"], ["C1", "South", "Feb"]])
    result = answer(summary, index)
    assert_blocked(result, "중복")
    assert "Orders.Period = Customers.Period" in result.answer
    assert "자동 적용하지 않았습니다" in result.answer
    assert "합계 10" not in result.answer and "합계 20" not in result.answer


def test_extra_key_suggestion_uses_changed_source_labels_not_business_names():
    summary, index = relational_fixture(
        left=[["Record", "Customer ID", "Amount", "구분 코드"], ["ORD-1", "C1", 10, "X"], ["ORD-2", "C1", 20, "Y"]],
        right=[["Customer ID", "Region", "구분 코드"], ["C1", "North", "X"], ["C1", "South", "Y"]],
        names=("거래", "마스터"), offset=(8, 5))
    result = answer(summary, index, "거래와 마스터를 Customer ID로 연결해서 Region별 Amount 합계")
    assert_blocked(result, "중복")
    assert "거래.구분 코드 = 마스터.구분 코드" in result.answer


def test_nonunique_additional_key_is_never_suggested():
    summary, index = relational_fixture(
        left=[["Record", "Customer ID", "Amount", "Period"], ["ORD-1", "C1", 10, "Jan"]],
        right=[["Customer ID", "Region", "Period"], ["C1", "North", "Jan"], ["C1", "South", "Jan"]])
    result = answer(summary, index)
    assert_blocked(result, "중복")
    assert "추가 키 후보" not in result.answer


def test_key_hint_never_suggests_a_key_that_hides_unmatched_source_rows():
    summary, index = relational_fixture(
        left=[["Record", "Customer ID", "Amount", "Period"], ["ORD-1", "C1", 10, "Jan"], ["ORD-2", "C1", 20, "Missing"]],
        right=[["Customer ID", "Region", "Period"], ["C1", "North", "Jan"], ["C1", "South", "Feb"]])
    result = answer(summary, index)
    assert_blocked(result, "중복")
    assert "추가 키 후보" not in result.answer


def test_blank_composite_component_cannot_hide_an_error_in_another_component():
    summary, index = relational_fixture(
        left=[["Record", "Customer ID", "Amount", "Period"], ["ORD-1", None, 10, "#N/A"], ["ORD-2", "C1", 20, "Feb"]],
        right=[["Customer ID", "Region", "Period"], [None, "North", "#N/A"], ["C1", "South", "Feb"]])
    result = answer(summary, index, "Orders와 Customers를 Customer ID 및 Period로 연결해서 Region별 Amount 합계",
                    on=[{"left_column_id": "B", "right_column_id": "A"}, {"left_column_id": "D", "right_column_id": "C"}])
    assert_blocked(result, "오류")
