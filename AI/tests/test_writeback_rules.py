"""A model's reading of an edit is applied to every matching source row, or not at all."""
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.agent.query.tabular_query_models import TabularFilter
from app.agent.writeback.models import WritebackProposalDraft, WritebackRuleDraft
from app.api.workbook_writebacks import get_writeback_generator
from app.main import app
from tests.support.workbook_api_fixtures import upload

ROWS = [("Cookies", "Chip", 1.7699999999999998, 3), ("Bars", "Carrot", 2.0, 4),
        ("Cookies", "Oat", 2.5, 5), ("Cookies", "Chip", 3.0, 6)]


def _content():
    book = Workbook()
    sales = book.active
    sales.title = "Sales"
    sales.append(["Category", "Product", "UnitPrice", "Qty", "TotalPrice"])
    for number, (category, product, price, qty) in enumerate(ROWS, start=2):
        sales.append([category, product, price, qty, f"=C{number}*D{number}"])
    totals = book.create_sheet("Totals")
    totals.append(["Category", "Total"])
    totals.append(["Cookies", 100])
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def _propose(instruction, **rule):
    rule = {"table_id": "Sales!A1:E5", "target_column_id": "UnitPrice", "operation": "percent_increase",
            "amount": 10, "reading": "‘쿠키’ → Category = Cookies, ‘단가’ → UnitPrice",
            "filters": [TabularFilter(column_id="Category", operator="equals", value="Cookies")], **rule}

    class Stub:
        async def generate(self, instruction, filename, context):
            assert any(table["table_id"] == "Sales!A1:E5" for table in context["tables"])
            return WritebackProposalDraft(summary="해석", rules=[WritebackRuleDraft(**rule)])
    app.dependency_overrides[get_writeback_generator] = Stub
    try:
        return TestClient(app).post("/api/v1/workbooks/writeback-proposals", data={"instruction": instruction},
                                    files=upload("sales.xlsx", _content())).json()
    finally:
        app.dependency_overrides.clear()


def _changes(body):
    return {change["reference"]: change["new_value"] for change in body["changes"]}


def test_a_korean_request_reaches_every_matching_row_with_computed_values() -> None:
    body = _propose("쿠키 단가를 10% 올려줘")
    assert body["status"] == "ready", body
    assert _changes(body) == {"C2": 1.947, "C4": 2.75, "C5": 3.3}
    assert "Category’ = Cookies인 3개 행" in body["limitations"][0] and "‘쿠키’ → Category" in body["limitations"][0]


def test_a_stated_value_is_written_to_every_row() -> None:
    body = _propose("쿠키 단가를 모두 4로 바꿔줘", operation="set", amount="4")
    assert _changes(body) == {"C2": 4, "C4": 4, "C5": 4}


def test_unsafe_or_unstated_readings_block_every_row() -> None:
    cases = [
        ("쿠키 판매금액을 10% 올려줘", {"target_column_id": "TotalPrice"}),  # formulas stay formulas
        ("쿠키 단가를 10% 올려줘", {"amount": 20}),  # not the stated calculation
        ("쿠키 단가를 4로 바꿔줘", {"operation": "set", "amount": "5"}),  # not the stated value
        ("쿠키 단가를 10% 올려줘", {"filters": [TabularFilter(column_id="Category", operator="equals", value="쿠키")]}),
    ]
    for instruction, rule in cases:
        body = _propose(instruction, **rule)
        assert body["status"] == "blocked" and not body["changes"], (instruction, body)
        assert body["risks"]





def test_a_reading_naming_nothing_in_the_source_falls_back_to_the_checked_cell_path() -> None:
    body = _propose("쿠키 단가를 10% 올려줘", target_column_id="Price")
    assert body["status"] == "blocked" and not body["changes"]


def test_a_date_range_selects_rows_by_their_source_dates() -> None:
    from datetime import datetime
    from app.agent.writeback.rule_execution import _rows

    class Row:
        def __init__(self, day, category):
            self.values = {"A": day, "B": category}
    class Table:
        rows = [Row("2022-12-31T00:00:00", "Cookies"), Row("2023-01-01T00:00:00", "Cookies"),
                Row(datetime(2023, 6, 1), "Bars"), Row("2024-01-01T00:00:00", "Cookies")]
        columns = ()
    year = [TabularFilter(column_id="A", operator="greater_than_or_equal", value="2023-01-01T00:00:00"),
            TabularFilter(column_id="A", operator="less_than", value="2024-01-01")]
    assert [row.values["A"] for row in _rows(Table, year)] == ["2023-01-01T00:00:00", datetime(2023, 6, 1)]
    Table.rows = [*Table.rows, Row("미정", "Bars")]
    assert _rows(Table, year) is None


def test_a_titled_table_with_notes_below_is_narrowed_to_its_record_rows() -> None:
    from app.agent.writeback.writeback_tables import _narrowed

    rows = [["Percentage of days with good air quality, 2021-2023"], ["Year", "Good", "Unhealthy"],
            [2021, 0.4, 0.03], [2022, 0.4, 0.03], [2023, 0.4, 0.03], ["Data: U.S. EPA"], ["Note: AQI based"]]
    cells = {f"{'ABC'[column]}{number}": {"value": value}
             for number, row in enumerate(rows, start=1) for column, value in enumerate(row)}
    assert _narrowed("A1:C7", cells) == "A2:C5"
    assert _narrowed("A2:C5", cells) is None  # already exact: nothing to add
