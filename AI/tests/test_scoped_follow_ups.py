"""A clarification's follow-up is answered within its scope, with a month named in Korean."""
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from tests.support.large_workbook_fixtures import offline, parsed, tiny_caps, workbook  # noqa: F401 (fixtures)
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Month", "Beds"], ["November 2025", 95_100], ["December 2025", 95_087]]


def _ask(question, month):
    summary, index = table_fixture([(1, 1, ROWS)], sheet_name="Beds")
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=["B"], statistic="all",
                            filters=[TabularFilter(column_id="A", operator="equals", value=month)])
    return execute_tabular_query(plan, summary, index, question)


def test_a_month_written_as_text_is_the_month_the_question_names():
    assert "95,087" in _ask("2025년 12월 Beds 값은?", "December 2025").answer
    assert _ask("2025년 12월 Beds 값은?", "November 2025") is None


def test_the_scope_of_a_follow_up_is_not_read_as_a_condition():
    question = "'Beds'!A1:B3 범위의 B열 Beds 기준으로: 2025년 12월 Beds 값은?"
    assert "95,087" in _ask(question, "December 2025").answer
    assert _ask("'Beds'!A1:B2 범위의 B열 Beds 기준으로: 2025년 12월 Beds 값은?", "December 2025") is None  # row 3 outside


def test_a_column_is_read_over_the_whole_source_table_when_the_summary_sampled_it(tiny_caps):
    from app.agent.query.tabular_column_values import column_values
    matrix = [["Name", "Population"], *([f"Area {number}", number] for number in range(1, 40)), ["LONDON", 9_089_736]]
    summary, index, _ = parsed(workbook({"Persons": matrix}))
    table = build_query_tables(summary)[0]
    assert not table.complete and "LONDON" not in [row.values.get("A") for row in table.rows]
    assert "LONDON" in column_values(table, "A", index)


def test_a_ranked_list_of_a_percent_column_reads_its_shares_as_stored():
    from app.agent.query.tabular_advanced_language import advanced_operations_match
    rows = [["Month", "Occupancy (%)"], ["November 2025", 0.93], ["December 2025", 0.92]]
    summary, _ = table_fixture([(1, 1, rows)], sheet_name="Beds")
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_list", table_id=table.id, column_ids=["A", "B"], order_by="B",
                            descending=True, limit=1)
    # "점유율" names the stored rate beside the Month label, not a share to compute.
    assert advanced_operations_match("병상 점유율이 가장 높았던 달은?", plan, table) is True


def test_a_name_written_as_a_and_b_is_one_label():
    from app.agent.query.joined_names import joined_names
    assert "잉글랜드와 웨일스" in joined_names(["잉글랜드", "웨일스"], "잉글랜드와 웨일스 인구는 얼마야?")
    assert joined_names(["쿠키"], "쿠키 판매수량은?") == ["쿠키"]
