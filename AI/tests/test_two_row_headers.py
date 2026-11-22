"""A merged parent header over child headers names each column by both: "2024 상반기"."""
from io import BytesIO

from openpyxl import Workbook

from app.agent.query.tabular_catalog import build_query_tables
from app.services.workbook_parser import parse_workbook


def test_a_merged_parent_over_children_names_each_column_by_both():
    book = Workbook()
    sheet = book.active
    sheet.append(["제품", "2023", None, "2024", None])
    sheet.append([None, "상반기", "하반기", "상반기", "하반기"])
    sheet.merge_cells("B1:C1")
    sheet.merge_cells("D1:E1")
    sheet.merge_cells("A1:A2")
    for name, *values in [["노트북", 228, 122, 88, 383], ["태블릿", 237, 296, 274, 351], ["모니터", 263, 146, 178, 216]]:
        sheet.append([name, *values])
    stream = BytesIO()
    book.save(stream)
    tables = build_query_tables(parse_workbook("h.xlsx", stream.getvalue()))
    table = next(table for table in tables if len(table.columns) == 5)
    assert [column.header for column in table.columns] == ["제품", "2023 상반기", "2023 하반기", "2024 상반기", "2024 하반기"]
    assert table.rows[0].values["E"] == 383 and len(table.rows) == 3
