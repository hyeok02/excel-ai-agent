"""A filter value that is another table's column name, and a SUM row inside a summed column."""
from io import BytesIO
from types import SimpleNamespace

from openpyxl import Workbook

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.question_index import build_question_data_index
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_routing import planned_tabular_answer
from app.agent.query.tabular_subtotal_rows import without_subtotals
from app.services.workbook_parser import parse_workbook


def _workbook():
    book = Workbook()
    sales = book.active
    sales.title = "Sales"
    for row in (["Region", "Amount"], ["East", 10], ["West", 5], ["East", 7]):
        sales.append(row)
    totals = book.create_sheet("Totals")
    for row in (["Category", "East", "West"], ["Bars", 3, 4], ["Cookies", 6, 1]):
        totals.append(row)
    output = BytesIO()
    book.save(output)
    content = output.getvalue()
    summary = parse_workbook("sales.xlsx", content)
    return summary, build_question_data_index("sales.xlsx", content, summary)


def test_a_value_named_like_another_tables_column_still_filters_its_own_table():
    summary, index = _workbook()
    plan = TabularQueryPlan(operation="numeric_summary", table_id="Sales!A1:B4", column_ids=["B"], statistic="sum",
                            filters=[TabularFilter(column_id="A", operator="equals", value="East")])
    answer = planned_tabular_answer(QuestionIntent(False, "aggregation", (), True, plan), summary, index,
                                    "East Amount 합계는?")
    assert answer.status == "answered" and "합계 17" in answer.answer, answer.answer


def test_a_sum_row_over_the_summed_rows_is_not_counted_twice():
    row = lambda number, formula=None: SimpleNamespace(row_number=number, formulas={"C": formula} if formula else {})
    rows = [row(5), row(6), row(7), row(8), row(9, "=SUM(C5:C8)")]
    kept, notes = without_subtotals(rows, ["C"], "Totals")
    assert [item.row_number for item in kept] == [5, 6, 7, 8] and "Totals!C9" in notes[0]
    # A SUM over rows that are not all summed here, or over another column, is left alone.
    for formula in ("=SUM(C4:C8)", "=SUM(D5:D8)", "=SUMIFS(C5:C8,B5:B8,\"x\")"):
        assert len(without_subtotals([*rows[:4], row(9, formula)], ["C"], "Totals")[0]) == 5
