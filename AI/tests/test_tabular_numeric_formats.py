from io import BytesIO

import pytest
from openpyxl import Workbook
from openpyxl.worksheet.table import Table

from app.agent.query.index import build_workbook_data_index
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_numeric import numeric_summary
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.services.workbook_parser import parse_workbook


@pytest.mark.parametrize("values,formats,total,average,minimum,maximum", [
    ([0.1, 0.2], ["0%", "0%"], "30%", "15%", "10%", "20%"),
    ([0.1, 0.2], ["General", "General"], "0.3", "0.15", "0.1", "0.2"),
    ([0.1, 0.2], ["$0.00", "$0.00"], "$0.30", "$0.15", "$0.10", "$0.20"),
    ([1000, 2000], ['0,"kg"', '0,"kg"'], "3kg", "1.5kg", "1kg", "2kg"),
    ([1, 2], ["0", "0"], "3", "1.5", "1", "2"),
])
def test_aggregates_keep_source_units_without_float_artifacts(values, formats, total, average,
                                                             minimum, maximum):
    text, limitations = numeric_summary(values, formats)

    assert f"합계 {total}," in text and f"평균 {average}," in text
    assert f"최솟값 {minimum}," in text and f"최댓값 {maximum}," in text
    assert "00000000000000004" not in text and not limitations


@pytest.mark.parametrize("formats", [
    ["0%", "General"], ["$0.00", "€0.00"], ["0,", "0"],
    ['0"%"', "0%"], ["yyyy-mm-dd", "yyyy-mm-dd"],
])
def test_incompatible_units_or_unsupported_date_formats_are_not_aggregated(formats):
    assert numeric_summary([0.1, 0.2], formats) == (None, [])


def test_blank_cells_do_not_define_the_aggregate_unit():
    text, _ = numeric_summary([0.1, None, 0.2], ["0%", "General", "0.0%"])

    assert "합계 30.0%" in text and "빈칸 1건" in text


def _formatted_source():
    book = Workbook()
    sheet = book.active
    for row in [["Record", "Measurement", "Group"], ["a", 0.1, "first"],
                ["b", 0.2, "first"], ["c", 200, "second"]]:
        sheet.append(row)
    sheet["B2"].number_format = "0%"
    sheet["B3"].number_format = "0%"
    sheet["B4"].number_format = "$0.00"
    sheet.add_table(Table(displayName="Values", ref="A1:C4"))
    output = BytesIO()
    book.save(output)
    content = output.getvalue()
    summary = parse_workbook("formats.xlsx", content)
    index = build_workbook_data_index("formats.xlsx", content)
    return summary, index


def test_filtered_aggregates_use_formats_of_selected_source_cells():
    summary, index = _formatted_source()
    table = build_query_tables(summary)[0]
    assert table.columns[1].number_formats == ("0%", "$0.00")
    assert table.rows[0].number_formats["B"] == "0%"
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"],
                            filters=[TabularFilter(column_id="C", operator="equals", value="first")])

    answer = execute_tabular_query(plan, summary, index, "선택한 값의 통계")

    assert answer is not None and "합계 30%" in answer.answer and "평균 15%" in answer.answer
    assert execute_tabular_query(plan.model_copy(update={"filters": []}), summary, index, "전체 통계") is None


def test_stale_format_metadata_cannot_change_verified_units():
    summary, index = _formatted_source()
    table = build_query_tables(summary)[0]
    for region in summary.sheets[0].regions:
        for row in region.analysis_rows:
            for cell in row:
                if cell["address"] in {"B2", "B3"}:
                    cell["number_format"] = "$0.00"
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id, column_ids=["B"])

    assert execute_tabular_query(plan, summary, index, "전체 통계") is None
