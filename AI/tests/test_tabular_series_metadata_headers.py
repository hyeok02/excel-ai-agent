"""Human headers and period columns survive a bold dataset-code metadata row."""
from dataclasses import replace

import pytest
from openpyxl import Workbook
from openpyxl.styles import Font

from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_metadata_headers import recover_series_header_range
from app.agent.query.tabular_query_models import TabularQueryPlan
from app.agent.query.tabular_validation import validated_table
from tests.support.large_workbook_fixtures import offline, parsed


def _workbook(start_row=4, start_column=1):
    book = Workbook()
    sheet = book.active
    sheet.title = "Different time series"
    rows = [["Observation period", "Average annual output", "Average annual inputs"],
            ["Series identifier codes", "AZ1", "BY2"],
            ["2021 Jan", 10, 100], ["2021 Feb", 20, 200], ["2021 Mar", 30, 300]]
    for row, values in enumerate(rows, start_row):
        for column, value in enumerate(values, start_column):
            cell = sheet.cell(row, column, value)
            if row == start_row + 1 and column > start_column:
                cell.font = Font(bold=True)
    return book


@pytest.mark.parametrize("start_row,start_column", [(4, 1), (12, 8)])
def test_descriptive_header_and_identity_column_are_recovered_without_dataset_names(start_row, start_column):
    summary, index, _ = parsed(_workbook(start_row, start_column))
    table = build_query_tables(summary)[0]
    assert [column.header for column in table.columns] == [
        "Observation period", "Average annual output", "Average annual inputs"]
    assert table.metadata_rows == frozenset({start_row + 1})
    assert [row.row_number for row in table.rows] == [start_row + 2, start_row + 3, start_row + 4]
    assert validated_table(table, index, {table.columns[1].id})
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=[table.columns[1].id], statistic="sum")
    answer = execute_tabular_query(plan, summary, index, "Average annual output 합계")
    assert answer is not None and "합계 60" in answer.answer
    assert answer.verification.level == "request_checked"


def test_metadata_is_skipped_only_after_source_validation_in_full_stream():
    summary, index, _ = parsed(_workbook())
    table = build_query_tables(summary)[0]
    index = replace(index, rows=tuple(row for row in index.rows if row.row_number <= 5),
                    truncated=True, truncated_sheet_names=frozenset({table.sheet_name}))
    plan = TabularQueryPlan(operation="row_count", table_id=table.id)
    answer = execute_tabular_query(plan, summary, index, "Different time series 시트 전체 행 개수")
    assert answer is not None and "3건" in answer.answer
    assert "full_source_scan" in answer.verification.checks


def test_unlabeled_alphanumeric_records_are_not_silently_discarded_as_metadata():
    cells = {"A3": {"value": "Period"}, "B3": {"value": "Long category title"},
             "C3": {"value": "Long component title"},
             "A4": {"value": "Current"}, "B4": {"value": "AZ1"}, "C4": {"value": "BY2"}}
    assert recover_series_header_range("B4:C8", cells) == "B4:C8"


def test_forged_metadata_exclusion_cannot_hide_a_real_record():
    summary, index, _ = parsed(_workbook())
    table = build_query_tables(summary)[0]
    forged = replace(table, metadata_rows=frozenset({5, 6}),
                     rows=tuple(row for row in table.rows if row.row_number != 6))
    assert not validated_table(forged, index, {table.columns[1].id})
