from io import BytesIO

import pytest
from openpyxl.pivot.cache import CacheField, WorksheetSource
from openpyxl.pivot.table import DataField, FieldItem, PageField

from app.services.workbook_parser import parse_workbook
from app.services.workbook_parsing.pivot_units import pivot_unit_sources
from tests.support.pivot_unit_fixtures import _book


def test_native_pivot_provenance_survives_serialization_and_parser():
    workbook, summary, _ = _book()
    output = BytesIO()
    workbook.save(output)
    result = parse_workbook("arbitrary.xlsx", output.getvalue())
    sheet = next(sheet for sheet in result.sheets if sheet.name == summary.title)
    assert sheet.pivot_unit_sources == [{
        "source_sheet": "Transactions", "source_range": "A1:C5",
        "source_column": "C", "source_header": "Amount", "total_value": 100,
        "total_cell": "D7", "number_format": '"$"#,##0.00',
        "reference": "'Owner''s Summary'!D7",
    }]
    assert not next(sheet for sheet in result.sheets if sheet.name == "Transactions").pivot_unit_sources


def test_direct_worksheet_source_and_non_dollar_format_are_retained():
    workbook, summary, pivot = _book()
    pivot.cache.cacheSource.worksheetSource = WorksheetSource(sheet="Transactions", ref="$A$1:$C$5")
    summary["D7"].number_format = '"€"#,##0.00'
    result = pivot_unit_sources(workbook, summary, summary)
    assert result[0]["source_range"] == "A1:C5"
    assert result[0]["number_format"] == '"€"#,##0.00'


def test_arbitrary_table_sheet_and_field_names_use_native_identity():
    workbook, summary, pivot = _book()
    source = workbook["Transactions"]
    source.title = "원본 거래"
    source.tables["Orders"].name = "Renamed_Orders"
    pivot.cache.cacheSource.worksheetSource.name = "Renamed_Orders"
    source["C1"] = "청구액"
    pivot.cache.cacheFields[2].name = "청구액"
    result = pivot_unit_sources(workbook, summary, summary)
    assert result[0]["source_sheet"] == "원본 거래"
    assert result[0]["source_header"] == "청구액"
    assert result[0]["source_column"] == "C"


def test_optional_metadata_has_bounded_size():
    workbook, summary, pivot = _book()
    summary._pivots = [pivot] * 100
    assert len(pivot_unit_sources(workbook, summary, summary)) == 64


@pytest.mark.parametrize("changed", [
    "percent", "average", "multiple", "page_filter", "hidden_item", "calculated_field",
    "no_row_total", "no_col_total", "not_grand", "layout_count", "source_header",
    "missing_table", "external", "cache_width", "invalid_field", "entire_column",
    "outside_source", "outside_pivot", "formula_total", "boolean_total", "missing_total",
    "table_totals",
])
def test_ambiguous_or_transformed_pivot_is_not_unit_evidence(changed):
    workbook, summary, pivot = _book()
    if changed == "percent":
        pivot.dataFields[0].showDataAs = "percentOfCol"
    elif changed == "average":
        pivot.dataFields[0].subtotal = "average"
    elif changed == "multiple":
        pivot.dataFields.append(DataField(name="Other", fld=2))
    elif changed == "page_filter":
        pivot.pageFields.append(PageField(fld=0))
    elif changed == "hidden_item":
        pivot.pivotFields[0].items.append(FieldItem(x=0, h=True))
    elif changed == "calculated_field":
        pivot.cache.cacheFields[2].formula = "Amount*2"
    elif changed == "no_row_total":
        pivot.rowGrandTotals = False
    elif changed == "no_col_total":
        pivot.colGrandTotals = False
    elif changed == "not_grand":
        pivot.rowItems[-1].t = "data"
    elif changed == "layout_count":
        pivot.location.firstDataRow = 1
    elif changed == "source_header":
        workbook["Transactions"]["C1"] = "Quantity"
    elif changed == "missing_table":
        pivot.cache.cacheSource.worksheetSource.name = "Missing"
    elif changed == "external":
        pivot.cache.cacheSource.type = "external"
    elif changed == "cache_width":
        pivot.cache.cacheFields.append(CacheField(name="Other"))
    elif changed == "invalid_field":
        pivot.dataFields[0].fld = -1
    elif changed == "entire_column":
        pivot.cache.cacheSource.worksheetSource = WorksheetSource(sheet="Transactions", ref="A:C")
    elif changed == "outside_source":
        pivot.cache.cacheSource.worksheetSource = WorksheetSource(sheet="Transactions", ref="A1:C100")
    elif changed == "outside_pivot":
        pivot.location.ref = "A3:XFD1048576"
    elif changed == "formula_total":
        summary["D7"] = "=100"
    elif changed == "boolean_total":
        summary["D7"] = True
    elif changed == "missing_total":
        summary["D7"] = None
    elif changed == "table_totals":
        workbook["Transactions"].tables["Orders"].totalsRowCount = 1
    assert pivot_unit_sources(workbook, summary, summary) == []


def test_matching_unrelated_summary_without_native_link_is_ignored():
    workbook, summary, _ = _book()
    summary._pivots.clear()
    assert summary["D7"].value == 100
    assert pivot_unit_sources(workbook, summary, summary) == []
