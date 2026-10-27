"""Unbounded source rows are excluded only when their entire range is outside."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_filters import matches
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("label", ["6 and beyond", "6 or more", "6 이상"])
@pytest.mark.parametrize("threshold,expected", [(3, False), (6, None), (8, None)])
def test_lower_bucket_is_not_assigned_its_boundary_as_a_single_value(label, threshold, expected):
    condition = TabularFilter(column_id="A", operator="less_than_or_equal", value=threshold)
    assert matches(label, condition) is expected


@pytest.mark.parametrize("label,operator,threshold,expected", [
    ("6 and beyond", "greater_than_or_equal", 1, True),
    ("6 and beyond", "greater_than_or_equal", 6, True),
    ("6 and beyond", "greater_than", 6, None),
    ("6 초과", "greater_than", 6, True),
    ("less than 6", "less_than", 6, True),
    ("6 이하", "less_than", 6, None),
    ("6 and beyond", "equals", 3, False),
    ("6 and beyond", "equals", 8, None),
    ("6 and beyond", "not_equals", 8, None),
])
def test_open_closed_and_equality_predicates_require_whole_interval_proof(label, operator, threshold, expected):
    assert matches(label, TabularFilter(column_id="A", operator=operator, value=threshold)) is expected


@pytest.mark.parametrize("label", ["unknown", "6 maybe later", "6+", "Item 6 and beyond", "#PEND", "n/a"])
def test_unknown_labels_never_become_zero_or_false_numeric_predicates(label):
    assert matches(label, TabularFilter(column_id="A", operator="less_than_or_equal", value=3)) is None


@pytest.mark.parametrize("unit,style", [("percent", "General"), ("raw", "0%"), ("raw", '0"kg"')])
def test_scaled_or_unit_qualified_labels_are_not_reinterpreted(unit, style):
    assert matches("6 and beyond", TabularFilter(column_id="A", operator="less_than_or_equal", value=3,
                                                 value_unit=unit), style) is None


@pytest.mark.parametrize("upper,expected", [(3, 60), (8, None)])
def test_numeric_interval_lookup_preserves_a_source_tail_bucket(upper, expected):
    summary, index = table_fixture([(6, 4, [["Stage", "Reserved"],
        [1, 10], [2, 20], [3, 30], [4, 40], [5, 50], ["6 and beyond", 900]])], sheet_name="Rate converter")
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["E"], statistic="sum",
        filters=[TabularFilter(column_id="D", operator="greater_than_or_equal", value=1),
                 TabularFilter(column_id="D", operator="less_than_or_equal", value=upper)])
    question = f"Rate converter 시트 D6:E12에서 Stage가 1부터 {upper}인 Reserved 합계는 얼마야?"
    answer = execute_tabular_query(plan, summary, index, question)
    if expected is None:
        assert answer is None or answer.verification.level != "request_checked"
    else:
        assert answer and f"합계 {expected}" in answer.answer
        assert answer.verification.level == "request_checked"
