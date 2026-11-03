"""Native pivot and linked source fixture for unit provenance tests."""
from openpyxl import Workbook
from openpyxl.pivot.cache import CacheDefinition, CacheField, CacheSource, WorksheetSource
from openpyxl.pivot.table import (
    DataField, Location, PivotField, RowColField, RowColItem, TableDefinition,
)
from openpyxl.worksheet.table import Table


def _book():
    workbook = Workbook()
    source = workbook.active
    source.title = "Transactions"
    source.append(["Category", "Region", "Amount"])
    for row in [("A", "East", 10), ("A", "West", 20),
                ("B", "East", 30), ("B", "West", 40)]:
        source.append(row)
    source.add_table(Table(displayName="Orders", ref="A1:C5"))
    summary = workbook.create_sheet("Owner's Summary")
    for row in [(None,), (None,), ("Sum of Amount", "Region"),
                ("Category", "East", "West", "Grand Total"),
                ("A", 10, 20, 30), ("B", 30, 40, 70),
                ("Grand Total", 40, 60, 100)]:
        summary.append(row)
    for row in summary.iter_rows(min_row=5, max_row=7, min_col=2, max_col=4):
        for cell in row:
            cell.number_format = '"$"#,##0.00'
    pivot = TableDefinition(
        name="Totals", cacheId=1, dataCaption="Values",
        location=Location(ref="A3:D7", firstHeaderRow=1, firstDataRow=2, firstDataCol=1),
        pivotFields=[PivotField(axis="axisRow"), PivotField(axis="axisCol"),
                     PivotField(dataField=True)],
        rowFields=[RowColField(x=0)], colFields=[RowColField(x=1)],
        rowItems=[RowColItem(), RowColItem(), RowColItem(t="grand")],
        colItems=[RowColItem(), RowColItem(), RowColItem(t="grand")],
        dataFields=[DataField(name="Sum of Amount", fld=2, numFmtId=164)],
    )
    pivot.cache = CacheDefinition(
        cacheSource=CacheSource(type="worksheet", worksheetSource=WorksheetSource(name="Orders")),
        cacheFields=[CacheField(name=name) for name in ("Category", "Region", "Amount")],
        recordCount=4,
    )
    summary.add_pivot(pivot)
    return workbook, summary, pivot
