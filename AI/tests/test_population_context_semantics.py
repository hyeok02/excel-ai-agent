"""Control columns cannot override total markers or spill onto other metrics."""
from dataclasses import replace

import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_population_context import NumericPopulationContext
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.support.large_workbook_fixtures import offline, parsed, plan_for, tiny_caps, workbook
from tests.tabular_query_fixtures import table_fixture


def execute(matrix, *, column="B", question="Amount 합계", **fields):
    summary, index = table_fixture([(1, 1, matrix)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=[column], statistic="sum", **fields)
    return execute_tabular_query(plan, summary, index, question)


@pytest.mark.parametrize("header, role", [("Row Role", None), ("Row Role", "Unknown"),
                                         ("Row Type", "Invoice"), ("Row Role", "Detail")])
@pytest.mark.parametrize("total", ["Total", "Total Amount", "Amount Total", "Section subtotal"])
def test_role_column_never_hides_actual_total_label(header, role, total):
    result = execute([["Item", "Amount", header], ["A", 100, role],
                      ["B", 200, role], [total, 300, role]])
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"
    assert "합계 600" not in result.answer


def test_metric_qualified_total_without_role_column_is_still_a_total():
    result = execute([["Item", "Amount"], ["A", 100], ["B", 200], ["Total Amount", 300]])
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"


def test_real_name_containing_total_is_not_an_aggregation_operator():
    result = execute([["Company", "Amount", "Row Type"],
                      ["Total Solutions", 100, "Invoice"], ["Beta", 200, "Invoice"]])
    assert result.status == "answered" and "합계 300" in result.answer


@pytest.mark.parametrize("metric", ["Total Employees", "Headcount", "Quantity", "판매량", "건수"])
def test_report_currency_does_not_block_nonmonetary_measures(metric):
    matrix = [["Item", metric, "Revenue", "Currency"],
              ["A", 10, 100, "USD"], ["B", 20, 200, "EUR"]]
    result = execute(matrix, question=f"{metric} 합계")
    assert result.status == "answered" and "합계 30" in result.answer
    assert "Currency" not in result.answer
    financial = execute(matrix, column="C", question="Revenue 합계")
    assert financial.status == "insufficient_evidence" and financial.verification.level == "unverified"


@pytest.mark.parametrize("metric", ["Total Employees", "Quantity"])
def test_explicit_quantity_groups_retain_normal_aggregation(metric):
    matrix = [["Item", metric, "Revenue", "Currency", "Region"],
              ["A", 10, 100, "USD", "North"], ["B", 20, 200, "EUR", "North"]]
    result = execute(matrix, question=f"Region별 {metric} 합계", group_by=["E"])
    assert result.status == "answered" and "합계 30" in result.answer


def test_streamed_tail_total_and_blank_role_cannot_restore_double_count(tiny_caps):
    matrix = [["Record", "Amount", "Row Role"],
              *[[f"Item{n}", n, None] for n in range(1, 9)], ["Total Amount", 36, None]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    result = execute_tabular_query(plan_for(summary), summary, index, "Records 시트 Amount 합계")
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"


def test_streamed_currency_applies_only_to_money_column(tiny_caps):
    matrix = [["Record", "Quantity", "Revenue", "Currency"],
              *[[f"Item{n}", n, n * 100, "USD" if n < 8 else "EUR"] for n in range(1, 9)]]
    summary, index, _ = parsed(workbook({"Records": matrix}))
    result = execute_tabular_query(plan_for(summary), summary, index, "Records 시트 Quantity 합계")
    assert result.status == "answered" and "합계 36" in result.answer
    assert "full_source_scan" in result.verification.checks


def test_subtotals_and_overlapping_grand_total_are_not_added_again():
    result = execute([["Item", "Amount"], ["A subtotal", 100],
                      ["B subtotal", 200], ["Grand Total", 300]])
    assert result.status == "insufficient_evidence" and result.verification.level == "unverified"
    assert "합계 600" not in result.answer


def test_independent_source_groups_can_display_their_own_single_total():
    result = execute([["Item", "Amount", "Region"], ["A subtotal", 100, "North"],
                      ["B subtotal", 200, "South"]], question="Region별 Amount 합계", group_by=["C"])
    assert result.status == "answered"
    assert "합계 100" in result.answer and "합계 200" in result.answer


def test_cached_sum_formula_does_not_hide_metric_qualified_total_label():
    summary, _ = table_fixture([(1, 1, [["Item", "Amount"], ["A", 100],
                                       ["B", 200], ["Total Amount", 300]])])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["B"], statistic="sum")
    context = NumericPopulationContext(plan, table)
    assert all(context.add(row) for row in table.rows[:-1])
    cached_sum = replace(table.rows[-1], formulas={"B": "=SUM(B2:B3)"})
    assert not context.add(cached_sum)
    assert "중복 집계" in context.error
