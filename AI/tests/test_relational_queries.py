import pytest

from app.agent.query.relational_models import RelationalQueryPlan
from app.agent.query.relational_execution import relational_query_answer
from tests.relational_query_fixtures import answer, relational_fixture, relational_plan


@pytest.mark.parametrize("names,offset", [(("Orders", "Customers"), (1, 1)), (("배송 내역", "소속 정보"), (8, 5))])
def test_grouped_join_uses_source_ids_after_renaming_and_moving(names, offset):
    summary, index = relational_fixture(names=names, offset=offset)
    result = answer(summary, index, f"{names[0]}와 {names[1]}를 Customer ID로 연결해서 Region별 Amount 합계")
    assert result.status == "answered", result.answer
    assert "North" in result.answer and "합계 10" in result.answer
    assert "South" in result.answer and "합계 20" in result.answer
    assert result.verification.level == "source_checked"
    assert {item.sheet_name for item in result.evidence} == set(names)
    assert any(item.value == 20 and item.reference.endswith(str(offset[0] + 2)) for item in result.evidence)


def test_composite_keys_disambiguate_repeated_dimension_ids():
    summary, index = relational_fixture(
        left=[["Record", "Customer ID", "Amount", "Period"], ["ORD-1", "C1", 10, "Jan"], ["ORD-2", "C1", 20, "Feb"]],
        right=[["Customer ID", "Region", "Period"], ["C1", "North", "Jan"], ["C1", "South", "Feb"]])
    result = answer(summary, index, "Orders와 Customers를 Customer ID 및 Period로 연결해서 Region별 Amount 합계",
                    on=[{"left_column_id": "B", "right_column_id": "A"}, {"left_column_id": "D", "right_column_id": "C"}])
    assert result.status == "answered", result.answer
    assert "North" in result.answer and "South" in result.answer


def test_lookup_filters_one_source_and_preserves_exact_cell_evidence():
    summary, index = relational_fixture()
    result = answer(summary, index, "Orders와 Customers를 Customer ID로 연결해서 ORD-1의 Region과 Amount",
                    operation="lookup", column_ids=["right.B", "left.C"], group_by=[],
                    filters=[{"side": "left", "column_id": "A", "operator": "equals", "value": "ORD-1"}])
    assert result.status == "answered", result.answer
    assert "North" in result.answer and "10" in result.answer
    cells = {(item.sheet_name, item.reference, item.value) for item in result.evidence if item.kind == "cell"}
    assert ("Orders", "A2", "ORD-1") in cells and ("Customers", "B2", "North") in cells
    assert "South" not in result.answer


def test_left_join_keeps_unmatched_rows_distinct_from_zero():
    summary, index = relational_fixture(right=[["Customer ID", "Region"], ["C1", "North"], ["C3", "West"]])
    result = answer(summary, index, "Orders와 Customers를 Customer ID로 연결해서 Region과 Amount 목록",
                    operation="row_list", column_ids=["left.C", "right.B"], group_by=[])
    assert result.status == "limited", result.answer
    assert "20" in result.answer and "연결 안 됨 (값 없음)" in result.answer
    assert "연결 안 됨 1개" in result.answer


def test_explicit_matched_population_reports_dropped_rows():
    summary, index = relational_fixture(right=[["Customer ID", "Region"], ["C1", "North"], ["C3", "West"]])
    result = answer(summary, index, "Orders와 Customers를 Customer ID로 연결해서 매칭된 행의 Amount 합계",
                    group_by=[], population="matched_only", join_type="inner")
    assert result.status == "limited", result.answer
    assert "합계 10" in result.answer and "연결 안 됨 1개" in result.answer


def test_many_detail_rows_may_group_by_one_dimension_without_multiplication():
    summary, index = relational_fixture(left=[["Order ID", "Customer ID", "Amount"],
                                              ["ORD-1", "C1", 10], ["ORD-2", "C1", 20]])
    result = answer(summary, index)
    assert result.status == "answered", result.answer
    assert "합계 30" in result.answer


def test_grouped_count_counts_detail_rows_without_ignoring_group_by():
    summary, index = relational_fixture(left=[["Order ID", "Customer ID", "Amount"],
                                              ["ORD-1", "C1", 10], ["ORD-2", "C1", 20]])
    result = answer(summary, index, "Orders와 Customers를 Customer ID로 연결해서 Region별 건수",
                    operation="row_count", column_ids=[])
    assert result.status == "answered", result.answer
    assert "North; 왼쪽 원본 행 기준 2건" in result.answer


def test_group_projection_is_not_mistaken_for_a_repeated_right_numeric_measure():
    summary, index = relational_fixture(left=[["Order ID", "Customer ID", "Amount"],
                                              ["ORD-1", "C1", 10], ["ORD-2", "C2", 20], ["ORD-3", "C1", 30]])
    result = answer(summary, index, column_ids=["right.B", "left.C"], group_by=["right.B"])
    assert result.status == "answered", result.answer
    assert "Region=North; Orders.Amount: 합계 40" in result.answer
    assert "Region=South; Orders.Amount: 합계 20" in result.answer
    assert result.verification.level == "source_checked"


def test_group_projection_does_not_disable_right_numeric_measure_duplication_guard():
    summary, index = relational_fixture(
        left=[["Order ID", "Customer ID", "Amount"], ["ORD-1", "C1", 10], ["ORD-2", "C1", 20]],
        right=[["Customer ID", "Region", "Budget"], ["C1", "North", 100], ["C2", "South", 200]])
    result = answer(summary, index, "Orders와 Customers를 Customer ID로 연결해서 Region별 Budget 합계",
                    column_ids=["right.B", "right.C"], group_by=["right.B"])
    assert result.status == "insufficient_evidence", result.answer
    assert "중복 집계" in result.answer


def test_models_refuse_unknown_operations_and_arbitrary_plan_fields():
    summary, _ = relational_fixture()
    raw = relational_plan(summary).model_dump()
    with pytest.raises(ValueError):
        RelationalQueryPlan(**{**raw, "sql": "SELECT * FROM somewhere"})
    with pytest.raises(ValueError):
        RelationalQueryPlan(**{**raw, "operation": "execute"})


def test_absent_plan_preserves_other_answer_routes():
    assert relational_query_answer(None, None, None, "anything") is None
