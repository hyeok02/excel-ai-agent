"""A plan repair cannot move to a table that lacks a field the first reading named."""
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.replanning_scope import keeps_named_fields
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.tabular_query_fixtures import table_fixture

SALES = [["Region", "Category", "TotalPrice"], ["East", "Cookies", 10.5], ["West", "Bars", 3.0]]
TOTALS = [["Category", "East", "West"], ["Cookies", 40, 20], ["Bars", 10, 30]]


def _check(targets, table_index):
    summary, _ = table_fixture([(1, 1, SALES), (1, 6, TOTALS)])
    tables = build_query_tables(summary)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=tables[table_index].id, column_ids=["B"],
                            statistic="sum")
    first = QuestionIntent(False, "aggregation", targets, True, None)
    return keeps_named_fields(first, QuestionIntent(False, "aggregation", (), True, plan), summary)


def test_a_repair_onto_a_table_without_the_named_fields_is_refused():
    sales = next(index for index, table in enumerate(build_query_tables(table_fixture([(1, 1, SALES), (1, 6, TOTALS)])[0]))
                 if any(column.header == "TotalPrice" for column in table.columns))
    assert _check(("East", "Region", "TotalPrice"), 1 - sales) is False
    assert _check(("East", "Region", "TotalPrice"), sales) is True  # East is a Region value, not a field


def test_targets_naming_no_field_leave_the_repair_free():
    assert _check(("동부", "판매금액"), 0) is True and _check(("동부", "판매금액"), 1) is True


def test_a_plan_less_reading_hands_its_named_fields_and_their_table_to_the_repair():
    from app.agent.query.replanning_scope import named_field_hint
    summary, _ = table_fixture([(1, 1, SALES), (1, 6, TOTALS)])
    sales = next(table.id for table in build_query_tables(summary) if any(c.header == "TotalPrice" for c in table.columns))
    hint = named_field_hint(QuestionIntent(False, "aggregation", ("East", "Region", "TotalPrice"), True, None), summary)
    assert hint == {"named_fields": ["Region", "TotalPrice"], "tables_with_named_fields": [sales]}
    assert named_field_hint(QuestionIntent(False, "aggregation", ("동부",), True, None), summary) == {}
