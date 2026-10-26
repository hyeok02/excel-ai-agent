"""Independent arithmetic oracles for source controls, filters and regrouping."""
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture


def answer(matrix, question, **fields):
    summary, index = table_fixture([(3, 2, matrix)], sheet_name="Unseen Ledger")
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["C"], statistic="sum", **fields)
    return execute_tabular_query(plan, summary, index, question)


def unsafe(result):
    assert result is None or result.status == "insufficient_evidence" and result.verification.level == "unverified"


@pytest.mark.parametrize("control, values", [
    ("Currency", ["USD", "EUR"]), ("통화", ["USD", "EUR"]),
    ("Magnitude", ["million", "thousand"]), ("금액 단위", ["백만", "천"]),
    ("Unit", ["kg", "lb"]), ("단위", ["명", "천 명"]),
    ("Row Role", ["Detail", "Subtotal"]),
])
@pytest.mark.parametrize("reverse", [False, True])
def test_incompatible_population_never_certifies_sum(control, values, reverse):
    rows = [["A", 100, values[0]], ["B", 200, values[1]]]
    if reverse:
        rows.reverse()
    unsafe(answer([["Item", "Revenue", control], *rows], "Revenue 합계"))


@pytest.mark.parametrize("metric", ["Revenue", "Measurement", "Total Employees"])
def test_complete_population_with_one_explicit_unit_remains_answerable(metric):
    result = answer([["Item", metric, "Unit"], ["A", 12, "unit"], ["B", 8, "unit"]], f"{metric} 합계")
    assert result and "합계 20" in result.answer and "Unit: unit" in result.answer
    assert result.verification.level == "request_checked"
    assert "D3:D5" in {cell.reference for cell in result.evidence}


@pytest.mark.parametrize("question", ["USD Currency만 Revenue 합계", "Currency가 USD인 Revenue 합계"])
def test_explicit_currency_filter_does_not_require_exchange_conversion(question):
    result = answer([["Item", "Revenue", "Currency"], ["A", 100, "USD"],
                     ["B", 900, "EUR"], ["C", 50, "USD"]], question,
                    filters=[TabularFilter(column_id="D", operator="equals", value="USD")])
    assert result and "합계 150" in result.answer and "900" not in result.answer
    assert result.verification.level == "request_checked"


def test_currency_grouping_keeps_valid_separate_totals():
    result = answer([["Item", "Revenue", "Currency"], ["A", 100, "USD"],
                     ["B", 900, "EUR"], ["C", 50, "USD"]], "Currency별 Revenue 합계", group_by=["D"])
    assert result and 'Currency: "USD"' in result.answer and 'Currency: "EUR"' in result.answer
    assert "합계 150" in result.answer and "합계 900" in result.answer
    assert result.verification.level == "request_checked"


def test_cross_currency_share_is_not_made_from_separately_valid_groups():
    result = answer([["Item", "Revenue", "Currency"], ["A", 100, "USD"], ["B", 900, "EUR"]],
                    "Currency별 Revenue 합계와 전체 비중", group_by=["D"], share_of_total=True)
    unsafe(result)


@pytest.mark.parametrize("role_header", ["Row Role", "행 유형"])
def test_filtering_details_excludes_subtotals_without_blocking_valid_sum(role_header):
    result = answer([["Item", "Amount", role_header], ["A", 100, "Detail"],
                     ["B", 200, "Detail"], ["All", 300, "Subtotal"]],
                    f"{role_header}가 Detail인 Amount 합계",
                    filters=[TabularFilter(column_id="D", operator="equals", value="Detail")])
    assert result and "합계 300" in result.answer and "합계 600" not in result.answer


def test_exact_total_row_is_not_added_again_and_substrings_are_not_magic():
    result = answer([["Item", "Amount"], ["A", 100], ["B", 200], ["Total", 300]], "Amount 합계")
    unsafe(result)
    assert "상세 행과 합계·소계 행" in result.answer
    result = answer([["Item", "Amount"], ["Total Solutions", 100], ["B", 200]], "Amount 합계")
    assert result and "합계 300" in result.answer


@pytest.mark.parametrize("control", ["Region", "Category", "Year"])
def test_ordinary_dimensions_do_not_become_unit_controls(control):
    result = answer([["Item", "Amount", control], ["A", 100, "one"], ["B", 200, "two"]], "Amount 합계")
    assert result and "합계 300" in result.answer


def test_header_currency_conflict_is_not_hidden_by_uniform_row_control():
    unsafe(answer([["Item", "Revenue (USD)", "Currency"], ["A", 100, "EUR"], ["B", 200, "EUR"]],
                  "Revenue (USD) 합계"))


@pytest.mark.parametrize("value", ["USD / EUR", "", "not USD"])
def test_unresolved_explicit_currency_never_becomes_plain_certified_amount(value):
    unsafe(answer([["Item", "Revenue", "Currency"], ["A", 100, value], ["B", 200, value]], "Revenue 합계"))


def test_stale_control_value_is_checked_against_original_cells():
    summary, index = table_fixture([(1, 1, [["Item", "Revenue", "Currency"],
                                          ["A", 100, "USD"], ["B", 200, "EUR"]])])
    summary.sheets[0].regions[0].analysis_rows[2][2]["value"] = "USD"
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"], statistic="sum")
    assert execute_tabular_query(plan, summary, index, "Revenue 합계") is None


def test_record_types_are_not_themselves_incompatible_total_detail_roles():
    result = answer([["Item", "Amount", "Row Type"],
                     ["A", 100, "Invoice"], ["B", -20, "Credit Note"]], "Amount 합계")
    assert result.status == "answered" and "합계 80" in result.answer
