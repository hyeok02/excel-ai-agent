"""Column metadata codes and bare cell ranges cannot become row identifiers."""
from dataclasses import replace
import pytest

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_request_scope import explicit_ranges, request_matches_plan, rows_match_explicit_ranges
from app.agent.query.tabular_execution import execute_tabular_query
from tests.tabular_query_fixtures import table_fixture


def fixture():
    summary, _ = table_fixture([(4, 1, [["Period", "Index A", "Index B"],
        ["1988", 62.2, 900], ["1989", 65.1, 990]])], sheet_name="Renamed data")
    table = build_query_tables(summary)[0]
    return replace(table, columns=tuple(replace(column,
        source_identifiers=((f"Renamed data!{column.id}2", code),)) if code else column
        for column, code in zip(table.columns, [None, "ZX81", "QR72"])))


def plan(table, metric):
    return TabularQueryPlan(operation="lookup", table_id=table.id, column_ids=[metric],
        filters=[TabularFilter(column_id="A", operator="equals", value="1988")])


def test_only_the_selected_metadata_series_identifier_binds():
    table = fixture()
    assert request_matches_plan("ZX81의 1988년 값은?", plan(table, "B"), table, [table])
    assert not request_matches_plan("ZX81의 1988년 값은?", plan(table, "C"), table, [table])
    assert not request_matches_plan("ZX81와 QR72의 1988년 값은?", plan(table, "B"), table, [table])


def test_unknown_or_transaction_identifier_still_requires_a_row_filter():
    table = fixture()
    assert not request_matches_plan("RecordZX88의 1988년 값은?", plan(table, "B"), table, [table])
    stripped = replace(table, columns=tuple(replace(c, source_identifiers=()) for c in table.columns))
    assert not request_matches_plan("ZX81의 1988년 값은?", plan(stripped, "B"), stripped, [stripped])


def test_bare_ranges_are_bounds_and_not_spurious_record_ids():
    table = fixture()
    question = "Renamed data 시트의 A4:B5 범위에서 ZX81의 1988년 값은?"
    assert explicit_ranges(question, include_unqualified=True) == [("", "A4:B5")]
    assert request_matches_plan(question, plan(table, "B"), table, [table])
    assert rows_match_explicit_ranges(question, table, ["A", "B"], [table.rows[0]])
    assert not rows_match_explicit_ranges(question, table, ["A", "B"], [table.rows[1]])
    assert not rows_match_explicit_ranges(question, table, ["C"], [table.rows[0]])
    assert not request_matches_plan("A4:Z99 범위의 ZX81의 1988년 값", plan(table, "B"), table, [table])


def test_qualified_range_is_not_duplicated_and_unqualified_single_cell_stays_ambiguous():
    assert explicit_ranges("'Renamed data'!$A$4:$B$5 범위") == [("Renamed data", "A$4:B$5")]
    assert explicit_ranges("A12 항목 값") == []


@pytest.mark.parametrize("lower,upper", [(1, 3), (2, 4)])
def test_source_numeric_interval_preserves_both_inclusive_bounds(lower, upper):
    summary, index = table_fixture([(6, 4, [["Stage", "Reserved"],
        [1, 10], [2, 20], [3, 30], [4, 40], [5, 50], [6, 60]])], sheet_name="Schedule")
    table = build_query_tables(summary)[0]
    question = f"Schedule 시트의 D6:E12 표에서 Stage가 {lower}부터 {upper}인 Reserved 합계는 얼마야?"
    conditions = [TabularFilter(column_id="D", operator="greater_than_or_equal", value=lower),
                  TabularFilter(column_id="D", operator="less_than_or_equal", value=upper)]
    selected = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
        column_ids=["E"], statistic="sum", filters=conditions)
    result = execute_tabular_query(selected, summary, index, question)
    assert result and result.verification.level == "request_checked"
    assert f"합계 {sum(range(lower, upper + 1)) * 10}" in result.answer
    for wrong in [conditions[:1], conditions[1:],
                  [conditions[0], conditions[1].model_copy(update={"operator": "less_than"})],
                  [conditions[0], conditions[1].model_copy(update={"value": upper + 1})]]:
        assert execute_tabular_query(selected.model_copy(update={"filters": wrong}), summary, index, question) is None


@pytest.mark.parametrize("sheet", ["Rate converter", "Exchange rate source", "원가 환산 자료"])
def test_conversion_words_inside_sheet_name_are_source_scope_not_extra_operations(sheet):
    summary, index = table_fixture([(6, 4, [["Stage", "Reserved"], [1, 10], [2, 20], [3, 30]])],
                                   sheet_name=sheet)
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["E"],
        statistic="sum", filters=[TabularFilter(column_id="D", operator="greater_than_or_equal", value=1),
                                   TabularFilter(column_id="D", operator="less_than_or_equal", value=2)])
    question = f"{sheet} 시트의 D6:E9 표에서 Stage가 1부터 2인 Reserved 합계는 얼마야?"
    answer = execute_tabular_query(plan, summary, index, question)
    assert answer is not None and answer.verification.level == "request_checked"
    assert "합계 30" in answer.answer
    for conversion in ["달러로 환산해줘", "convert to USD", "exchange rate를 적용해줘"]:
        assert execute_tabular_query(plan, summary, index, question + " " + conversion) is None
