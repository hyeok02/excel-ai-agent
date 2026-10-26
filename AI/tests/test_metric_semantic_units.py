import asyncio

import pytest
from openpyxl import Workbook

from app.agent import create_default_tool_registry
from app.agent.query.service import WorkbookQuestionService
from tests.support.large_workbook_fixtures import NoGeneratedAnswer, parsed


def _answer(question, horizontal, number_format, financial=False):
    book = Workbook()
    sheet = book.active
    sheet.title = "Generic data"
    values = (100, 150) if financial else (2, 4)
    if horizontal:
        sheet.append(["Metric", "2024-01-01", "2025-01-01"])
        sheet.append(["Sales", *values])
        targets = ("B2", "C2")
    else:
        sheet.append(["Date", "Sales"])
        sheet.append(["2024-01-01", values[0]])
        sheet.append(["2025-01-01", values[1]])
        targets = ("B2", "B3")
    for address in targets:
        sheet[address].number_format = number_format
    summary, index = parsed(book, filename="generic-units.xlsx")[:2]
    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry())
    return asyncio.run(service.answer(question, summary, index))


@pytest.mark.parametrize("horizontal", [False, True])
@pytest.mark.parametrize("question", ["매출 추이 알려줘", "Revenue 추이 알려줘"])
@pytest.mark.parametrize("number_format", ['0"명"', '0" persons"'])
def test_explicit_people_units_block_revenue_alias_without_category_headers(horizontal, question, number_format):
    result = _answer(question, horizontal, number_format)
    assert result.status == "insufficient_evidence", result.model_dump()
    assert result.verification.level == "unverified"
    assert result.selected_tools == ["check_metric_semantics"]
    assert "인원" in result.answer and number_format in result.answer


@pytest.mark.parametrize("horizontal", [False, True])
@pytest.mark.parametrize("question", ["Sales 추이 알려줘", "Sales 인원 추이 알려줘"])
def test_original_sales_count_questions_remain_answerable(horizontal, question):
    result = _answer(question, horizontal, '0"명"')
    assert result.status == "answered", result.model_dump()
    assert "2명 → 4명" in result.answer


@pytest.mark.parametrize("horizontal", [False, True])
def test_real_currency_sales_keeps_its_revenue_alias(horizontal):
    result = _answer("매출 추이 알려줘", horizontal, '"USD "#,##0', financial=True)
    assert result.status == "answered", result.model_dump()
    assert "100" in result.answer and "150" in result.answer


def test_horizontal_units_stay_inside_own_label_and_period_axis():
    from app.agent.query.metric_row_semantics import row_metric_column
    from app.agent.query.metric_semantics import column_metric_conflict

    book = Workbook()
    sheet = book.active
    sheet.append(["Metric", "2024-01-01", "2025-01-01", "Note", "Metric", "2024-01-01", "2025-01-01"])
    sheet.append(["Sales", 100, 150, 999, "People", 2, 4])
    for address in ("B2", "C2"):
        sheet[address].number_format = '"USD "#,##0'
    for address in ("D2", "F2", "G2"):
        sheet[address].number_format = '0"명"'
    index = parsed(book)[1]
    axis, row = index.rows
    label = next(cell for cell in row.cells if cell.address == "A2")
    column = row_metric_column(label, axis, index.rows)
    assert column.sample_values == (100, 150)
    assert column.number_formats == ('"USD "#,##0',)
    assert not column_metric_conflict(column, "매출 추이 알려줘")


def test_currency_per_person_is_not_a_headcount_unit():
    from app.agent.query.metric_semantics import column_metric_conflict
    from app.agent.query.tabular_catalog_models import QueryColumn

    column = QueryColumn("B", "Sales", "Sheet!B1", (100, 150), number_formats=('0"원/명"',))
    assert not column_metric_conflict(column, "매출 추이 알려줘")
