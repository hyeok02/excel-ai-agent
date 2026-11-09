"""Questions reach tables under a title, with notes below, and with years as column names."""
from io import BytesIO

from openpyxl import Workbook

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.question_index import build_question_data_index
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularFilter, TabularQueryPlan
from app.agent.query.tabular_routing import planned_tabular_answer
from app.services.workbook_parser import parse_workbook


def _workbook():
    book = Workbook()
    sheet = book.active
    sheet.title = "Sheet1"
    for row in (["Indicator H1. Percentage of children with asthma, 2017-2020"], ["Attack", 2017, 2018, 2019, 2020],
                ["Attack", 0.041, 0.039, 0.033, 0.027], ["Current", 0.081, 0.075, 0.07, 0.058],
                ["DATA: Survey"], ['*"Current" represents children who still have asthma.']):
        sheet.append(row)
    for row in sheet.iter_rows(min_row=3, max_row=4, min_col=2):
        for cell in row:
            cell.number_format = "0.0%"
    notes = book.create_sheet("Notes")
    for row in (["About this file"], ["Item", "Text"], ["Source", "Survey"], ["Contact", "Team"], ["See the web."]):
        notes.append(row)
    output = BytesIO()
    book.save(output)
    content = output.getvalue()
    summary = parse_workbook("asthma.xlsx", content)
    return summary, build_question_data_index("asthma.xlsx", content, summary)


def _ask(question, filters=()):
    summary, index = _workbook()
    plan = TabularQueryPlan(operation="lookup", table_id="Sheet1!A2:E4", column_ids=["D"], filters=list(filters))
    return planned_tabular_answer(QuestionIntent(False, "cell_lookup", (), True, plan), summary, index, question)


def test_titled_numeric_tables_are_offered_but_text_only_notes_are_not():
    summary, _ = _workbook()
    assert [(table.id, [column.header for column in table.columns]) for table in build_query_tables(summary)] == [
        ("Sheet1!A2:E4", ["Attack", "2017", "2018", "2019", "2020"])]
    assert [table.id for table in build_query_tables(summary, text_regions=True)] == ["Sheet1!A2:E4", "Notes!A2:B4"]


def test_a_value_asked_without_its_row_lists_every_labelled_row():
    answer = _ask("2019년의 천식 유병률은 어떻게 돼?")
    assert answer.status == "answered", answer.answer
    assert answer.answer.splitlines()[1:] == ["Attack — 2019: 3.3%", "Current — 2019: 7.0%"]


def test_a_row_named_beside_a_year_column_is_that_rows_filter():
    answer = _ask("2019 Current 값 알려줘", [TabularFilter(column_id="A", operator="equals", value="Current")])
    assert answer.status == "answered" and answer.answer.endswith("2019: 7.0%"), answer.answer
