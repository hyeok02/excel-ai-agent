from dataclasses import replace

import pytest

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_validation import filtered_rows
from app.agent.tools.workbook_row_counts import build_row_count
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("start_row,start_col,name", [(1, 1, "Clients"), (8, 4, "배송 기록")])
def test_lookup_projects_every_requested_attribute_from_one_filtered_record(start_row, start_col, name):
    from openpyxl.utils import get_column_letter

    summary, index = table_fixture([(start_row, start_col, [
        ["Record ID", "Counterparty", "Amount ($000)"],
        ["ABCD56872", "Example North", 243.125],
        ["ABCD87823", "Example South", 980.75],
    ])], sheet_name=name)
    table = build_query_tables(summary)[0]
    key, label, amount = [get_column_letter(start_col + offset) for offset in range(3)]
    plan = TabularQueryPlan(
        operation="lookup", table_id=table.id, column_ids=[label, amount],
        filters=[TabularFilter(column_id=key, operator="equals", value="ABCD56872")],
    )
    result = execute_tabular_query(plan, summary, index, "ABCD56872의 Counterparty와 Amount ($000)")
    assert result.status == "answered"
    assert "Example North" in result.answer and "243.125" in result.answer
    assert "980.75" not in result.answer and "Example South" not in result.answer
    assert result.verification.level == "request_checked"


def test_numeric_condition_counts_only_one_table_and_does_not_mix_neighboring_funds():
    summary, index = table_fixture([
        (4, 2, [["Owner", "Percent (%)"], ["A", 5.3], ["B", 1], ["C", 0.8]]),
        (4, 7, [["Fund", "Percent (%)"], ["A1", 7.9], ["B1", 5.5], ["C1", 2.6]]),
    ])
    tables = build_query_tables(summary)
    plan = TabularQueryPlan(operation="row_count", table_id=tables[0].id, filters=[
        TabularFilter(column_id="C", operator="greater_than_or_equal", value=1, value_unit="percent"),
    ])
    result = execute_tabular_query(plan, summary, index, "Percent (%)가 1% 이상인 건수")
    assert "2건" in result.answer
    assert all(not evidence.reference.startswith("H") for evidence in result.evidence)


def test_percentage_filter_handles_fractional_and_percentage_point_storage():
    summary, _ = table_fixture([(1, 1, [
        ["Entity", "Share (%)"], ["A", 0.01], ["B", 0.009], ["C", 0.2],
    ])])
    table = build_query_tables(summary)[0]
    rows = tuple(replace(row, number_formats={"B": "0.00%"}) for row in table.rows)
    fractional = replace(table, rows=rows)
    condition = TabularFilter(column_id="B", operator="greater_than_or_equal", value=1, value_unit="percent")
    assert [row.row_number for row in filtered_rows(fractional, [condition])] == [2, 4]
    assert filtered_rows(table, [condition]) == []


def test_numeric_unknown_value_does_not_become_verified_zero_count():
    summary, index = table_fixture([(1, 1, [
        ["Entity", "Amount"], ["A", "#N/A"], ["B", 5],
    ])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_count", table_id=table.id, filters=[
        TabularFilter(column_id="B", operator="greater_than", value=10),
    ])
    assert execute_tabular_query(plan, summary, index, "Amount가 10보다 큰 건수") is None


def test_top_n_sum_is_computed_after_sorting_inside_selected_table():
    summary, index = table_fixture([(1, 1, [
        ["Investor", "Share (%)"], ["A", 1.2], ["B", 4.8], ["C", 2.3], ["D", 0.4],
    ])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"],
                            order_by="B", limit=2, statistic="sum")
    answer = execute_tabular_query(plan, summary, index, "Share (%) 상위 2개 합계")
    assert "합계 7.1" in answer.answer
    assert "평균" not in answer.answer and "숫자 2건" in answer.answer


def test_explicit_column_identifier_and_sheet_cannot_be_overridden_by_valid_plan():
    summary, index = table_fixture([(1, 1, [
        ["Record ID", "Funding Type", "Security Type"],
        ["ORDER20001", "Debt", "Preferred"], ["ORDER20002", "Equity", "Common"],
    ])])
    table = build_query_tables(summary)[0]
    wrong_field = TabularQueryPlan(operation="row_count", table_id=table.id, filters=[
        TabularFilter(column_id="C", operator="equals", value="Common"),
    ])
    assert execute_tabular_query(wrong_field, summary, index, "Funding Type이 Equity인 거래 건수") is None
    wrong_id = TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=["B"], filters=[
        TabularFilter(column_id="A", operator="equals", value="ORDER20002"),
    ])
    assert execute_tabular_query(wrong_id, summary, index, "ORDER20001의 Funding Type") is None


def test_lookup_cannot_be_answered_by_count_even_when_cells_exist():
    summary, index = table_fixture([(1, 1, [["Record", "Value"], ["A", 11], ["B", 12]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_count", table_id=table.id)
    intent = QuestionIntent(False, "cell_lookup", (), True, plan)
    assert execute_tabular_query(plan, summary, index, "총 금액이 얼마야?", intent) is None
    assert build_row_count([], {}, "총 거래금액을 알려줘") is None


def test_ambiguous_duplicate_key_is_not_presented_as_single_verified_lookup():
    summary, index = table_fixture([(1, 1, [["Key", "Amount"], ["A", 11], ["A", 12]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=["B"], filters=[
        TabularFilter(column_id="A", operator="equals", value="A"),
    ])
    assert execute_tabular_query(plan, summary, index, "A의 Amount") is None


@pytest.mark.parametrize("sheet_name", ["Sheet1", "Report2026", "보고서2"])
def test_source_sheet_name_is_not_mistaken_for_a_record_identifier(sheet_name):
    summary, index = table_fixture([(1, 1, [
        ["Category", "Amount"], ["North", 11], ["South", 12],
    ])], sheet_name=sheet_name)
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["B"], statistic="sum")
    result = execute_tabular_query(plan, summary, index, f"{sheet_name} 시트의 Amount 합계")
    assert result is not None and "합계 23" in result.answer
    assert result.verification.level == "request_checked"
