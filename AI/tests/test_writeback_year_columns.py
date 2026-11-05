"""Tables whose header names years (Indicator, 1997, 1998, …) take edits by row and year."""
from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.agent.query.tabular_query_models import TabularFilter
from app.agent.writeback.models import WritebackProposalDraft, WritebackRuleDraft
from app.agent.writeback.writeback_tables import writeback_catalog
from app.api.workbook_writebacks import get_writeback_generator
from app.main import app
from app.services.workbook_parser import parse_workbook
from tests.support.workbook_api_fixtures import upload


def _content():
    book = Workbook()
    sheet = book.active
    sheet.title = "Sheet1"
    sheet.append(["Indicator H1. Percentage of children with asthma, 2017-2020"])
    sheet.append(["Attack", 2017, 2018, 2019, 2020])
    sheet.append(["Attack", 0.041, 0.039, 0.033, 0.027])
    sheet.append(["Current", 0.081, 0.075, 0.07, 0.058])
    sheet.append(["DATA: Survey"])
    sheet.append(['*"Current" represents children who still have asthma.'])
    for row in sheet.iter_rows(min_row=3, max_row=4, min_col=2):
        for cell in row:
            cell.number_format = "0.0%"
    output = BytesIO()
    book.save(output)
    return output.getvalue()


def _propose(instruction, amount, operation="set", row="Attack", also=()):
    rule = WritebackRuleDraft(table_id="Sheet1!A2:E4", target_column_id="D", operation=operation, amount=amount,
                              also_target_column_ids=list(also),
                              reading="‘2019년’ → 2019", filters=[TabularFilter(column_id="A", operator="equals",
                                                                               value=row)])

    class Stub:
        async def generate(self, instruction, filename, context):
            return WritebackProposalDraft(summary="해석", rules=[rule])
    app.dependency_overrides[get_writeback_generator] = Stub
    try:
        return TestClient(app).post("/api/v1/workbooks/writeback-proposals", data={"instruction": instruction},
                                    files=upload("asthma.xlsx", _content())).json()
    finally:
        app.dependency_overrides.clear()


def test_year_header_table_is_offered_with_years_as_columns():
    catalog = writeback_catalog(parse_workbook("asthma.xlsx", _content()))
    assert [(table["table_id"], [column["header"] for column in table["columns"]]) for table in catalog] == [
        ("Sheet1!A2:E4", ["Attack", "2017", "2018", "2019", "2020"])]


def test_stated_percentage_is_stored_as_the_excel_number():
    for amount in ("1.3%", 1.3, 0.013):
        body = _propose("Attack의 2019년 값을 1.3%로 바꿔줘", amount)
        assert body["status"] == "ready"
        assert [(change["reference"], change["new_value"]) for change in body["changes"]] == [("D3", 0.013)]


def test_bare_number_without_percent_sign_is_not_rescaled():
    body = _propose("Current의 2019년 값을 0.05로 바꿔줘", 0.05, row="Current")
    assert [(change["reference"], change["new_value"]) for change in body["changes"]] == [("D4", 0.05)]
    body = _propose("Current의 2019년 값을 10% 올려줘", 10, operation="percent_increase", row="Current")
    assert [(change["reference"], round(change["new_value"], 6)) for change in body["changes"]] == [("D4", 0.077)]


def test_one_rule_changes_every_year_column_the_request_names():
    body = _propose("2018년부터 2020년까지 Current 값을 모두 5%로 바꿔줘", "5%", row="Current", also=("C", "E"))
    assert body["status"] == "ready"
    assert sorted((change["reference"], change["new_value"]) for change in body["changes"]) == [
        ("C4", 0.05), ("D4", 0.05), ("E4", 0.05)]


def test_a_reading_that_leaves_out_a_named_year_changes_nothing():
    body = _propose("2018년부터 2020년까지 Current 값을 모두 5%로 바꿔줘", "5%", row="Current", also=("C",))
    assert body["status"] == "blocked" and not body["changes"]
    assert any("2020년 열이 해석에서 빠졌습니다" in risk for risk in body["risks"])
    # Years the table does not have are not asked of the reading.
    body = _propose("2019년부터 2030년까지 Current 값을 모두 5%로 바꿔줘", "5%", row="Current", also=("E",))
    assert body["status"] == "ready"
