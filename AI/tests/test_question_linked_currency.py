"""Plain record numbers take the currency of a native pivot that totals exactly that column."""
from dataclasses import replace

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_routing import planned_tabular_answer
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Category", "TotalPrice"], ["Cookies", 108.46], ["Bars", 50.5], ["Cookies", 20.04]]
PIVOT = {"source_sheet": "Arbitrary", "source_range": "A1:B4", "source_column": "B", "source_header": "TotalPrice",
         "total_value": 179.0, "number_format": '_("$"* #,##0_);_("$"* \\(#,##0\\);_("$"* "-"_);_(@_)',
         "reference": "'Pivot'!D9"}


def _summary(**pivot):
    summary, index = table_fixture([(1, 1, ROWS)])
    sheet = replace(summary.sheets[0], pivot_unit_sources=[{**PIVOT, **pivot}])
    return replace(summary, sheets=[sheet]), index


def _sum(summary, index):
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"], statistic="sum",
                            filters=[TabularFilter(column_id="A", operator="equals", value="Cookies")])
    return planned_tabular_answer(QuestionIntent(False, "aggregation", (), True, plan), summary, index,
                                  "Cookies TotalPrice 합계는?")


def test_a_pivot_totalling_the_whole_column_lends_its_currency():
    answer = _sum(*_summary())
    assert answer.status == "answered" and "합계 $128.5 " in answer.answer, answer.answer


def test_a_pivot_that_does_not_total_this_exact_column_lends_nothing():
    for pivot in ({"total_value": 180.0}, {"source_range": "A1:B3"}, {"source_header": "Amount"},
                  {"number_format": "#,##0"}):
        answer = _sum(*_summary(**pivot))
        assert answer.status == "answered" and "합계 128.5 " in answer.answer, (pivot, answer.answer)


def test_group_totals_and_sums_keep_the_unit_the_cells_show():
    from types import SimpleNamespace

    from app.agent.query.ranked_group_units import shown_total, total_unit
    from app.agent.query.tabular_numeric import numeric_summary

    def table(style):
        rows = [SimpleNamespace(values={"B": value}, number_formats={"B": style}) for value in (1000, 2500.5)]
        return SimpleNamespace(rows=rows)
    assert shown_total(3500.5, total_unit(table("₩#,##0"), "B")) == "₩3,500.50"
    assert shown_total(3500, total_unit(table('#,##0"원"'), "B")) == "3,500원"
    assert shown_total(3500, total_unit(table("0%"), "B")) == "3,500"  # a summed percentage is not a percentage
    assert numeric_summary([1000, 2500], ["₩#,##0"] * 2, "sum")[0].startswith("합계 ₩3,500")
    assert numeric_summary([1000, 2500], ['#,##0"원"'] * 2, "sum")[0].startswith("합계 3,500원")
