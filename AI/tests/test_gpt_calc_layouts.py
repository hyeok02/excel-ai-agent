"""Tables read the way their layout means: month sheets as one list, a statement's row names under an empty
header, a list larger than the summary's sample read whole, ask-backs the question settles, and two groups
compared both shown."""
import asyncio
from io import BytesIO
from types import SimpleNamespace

import app.main  # noqa: F401  (the application's import order)
from openpyxl import Workbook

from app.agent.query.cell_display import _display_cell
from app.agent.query.gpt_calc_answers import fallback_answer
from app.agent.query.gpt_calc_choices import unneeded_choice
from app.agent.query.gpt_calc_full_rows import completed_tables
from app.agent.query.gpt_calc_stacked import statement_and_period_tables
from app.agent.query.question_index import build_question_data_index
from app.agent.query.tabular_catalog import build_query_tables
from app.services.workbook_parser import parse_workbook
from tests.test_gpt_calc_fallback import NOTHING, _Planner, _table


def _book(fill):
    book = Workbook()
    fill(book)
    stream = BytesIO()
    book.save(stream)
    summary = parse_workbook("t.xlsx", stream.getvalue())
    return summary, build_question_data_index("t.xlsx", stream.getvalue(), summary)


def _months(book):
    for place, month in enumerate(("January", "February", "March")):
        sheet = book.active if place == 0 else book.create_sheet()
        sheet.title = month
        sheet.append(["Invoice", "City", "Qty", *(["Note"] if place else []), "Total"])
        for number in range(25):
            sheet.append([f"{month[:3]}-{number}", "A" if number % 2 else "B", 1, *(["-"] if place else []),
                          place + 1 + number % 2])


def _statement(book):
    book.active.title = "IS"
    book.active.append([None, "2023A", "2024A"])
    for row in (["Net sales", 100, 120], ["Net income", 10, 15], [], ["Balance Sheet:"], ["Total assets", 300, 340]):
        book.active.append(row)


def test_month_sheets_are_one_list_and_a_statement_keeps_its_row_names():
    summary, index = _book(_months)
    stacked = statement_and_period_tables(build_query_tables(summary), index)[0]
    assert stacked.sheet_name == "January + February + March" and len(stacked.rows) == 75
    assert "Note" not in [column.header for column in stacked.columns]  # a column one sheet adds is left out
    assert sum(row.values["D"] for row in stacked.rows) == 25 * 6 + 12 * 3  # each sheet's Total under one column
    summary, index = _book(_statement)
    table = statement_and_period_tables(build_query_tables(summary), index)[0]
    names = [row.values["A"] for row in table.rows]
    assert table.columns[0].header == "항목" and "Net income" in names and "Total assets" in names


def test_a_list_larger_than_the_sample_is_read_whole():
    def fill(book):
        book.active.title = "Big"
        book.active.append(["id", "type", *(f"c{n}" for n in range(40))])
        for number in range(1200):
            book.active.append([number, "TV" if number % 4 == 0 else "Movie", *(number for _ in range(40))])
    summary, index = _book(fill)
    assert not any(table.complete for table in build_query_tables(summary))
    table = completed_tables(build_query_tables(summary), index)[0]
    assert len(table.rows) == 1200 and sum(row.values["B"] == "TV" for row in table.rows) == 300


def test_ask_backs_the_question_settles():
    options = lambda *scopes: SimpleNamespace(clarification_options=[SimpleNamespace(scope=s) for s in scopes])  # noqa
    assert unneeded_choice(options("'January'!A1:C9", "'February'!A1:C9"))
    assert unneeded_choice(options("'Summary'!B13", "'Summary'!C13", "'Summary'!D13"))  # one row: "가장 컸던 해"
    assert not unneeded_choice(options("'Summary'!B13", "'Other'!C9"))

    def fill(book):
        book.active.title = "Budget"
        for row in (["Source", "Amount"], ["Salary", 2900], ["Bonus", 2300]):
            book.active.append(row)
        expenses = book.create_sheet("Expenses")
        expenses.append(["Date", "Description", "Category", "Amount", "Paid by"])
        for day in range(1, 6):
            expenses.append([f"2026-11-0{day}", "Shop", "Food", 10 * day, "Emma"])
        for title in ("Copy A", "Copy B"):  # one layout twice: which one is still asked
            sheet = book.create_sheet(title)
            for row in (["Month", "Beds"], ["Jan", 1], ["Feb", 2]):
                sheet.append(row)
    summary, _ = _book(fill)
    assert unneeded_choice(options("'Budget'!A1:B3", "'Expenses'!A1:E6"), summary)
    assert not unneeded_choice(options("'Copy A'!A1:B3", "'Copy B'!A1:B3"), summary)


def test_two_groups_compared_are_both_shown_and_codes_have_no_separators():
    summary, index = _book(_months)
    plan = {"kind": "table", "method": "m", "cells": None,
            "table": _table(table=1, group_by=["City"], measure="Total", aggregate="mean", order="desc", pick="top", n=1)}
    answer = asyncio.run(fallback_answer("q", summary, index, NOTHING, _Planner(plan))).answer
    assert "1. A: 2" in answer and "2. B: 1" in answer  # "A와 B 중 높은 쪽": the other one shown too
    assert _display_cell(70119, "General", "Zip") == "70119" and _display_cell(70119, "General", "Count") == "70,119"


def test_a_group_its_lines_and_their_unit_name_each_row_and_loose_values_are_a_table():
    def fill(book):
        sheet = book.active
        sheet.title = "Budget"
        sheet.append([None, None, "Net Monthly", 4000])
        sheet.append([None, None, "Budget", 3500])
        sheet.append([])
        sheet.append([None, None, None, None, "January", "February"])
        for group, item, unit, values in (("Living", "Rent", "$", (1500, 1500)), (None, "Gas", "$", (50, 60)),
                                          (None, "Water", "$", (10, 10)), ("Transport", "Car", "$", (200, 210)),
                                          (None, "Bus", "$", (30, 30)), (None, "Gas", "$", (140, 150))):
            sheet.append([None, group, item, unit, *values])
    summary, index = _book(fill)
    tables = statement_and_period_tables(build_query_tables(summary), index)
    budget = next(table for table in tables if "E" in [column.id for column in table.columns])
    assert [column.header for column in budget.columns][:3] == ["항목", "구분", "단위"]
    assert [(row.values["C"], row.values["B"]) for row in budget.rows][-1] == ("Gas", "Transport")  # carried down
    pairs = next(table for table in tables if table.source_kind == "pairs")
    assert [(row.values["C"], row.values["D"]) for row in pairs.rows] == [("Net Monthly", 4000), ("Budget", 3500)]


def test_periods_named_in_a_column_are_compared_in_order():
    def fill(book):
        book.active.title = "Sales"
        book.active.append(["Fiscal_Year", "Revenue"])
        for year, value in (("FY21", 90), ("FY20", 100), ("FY21", 10), ("FY20", 0)):
            book.active.append([year, value])
    summary, index = _book(fill)
    plan = {"kind": "table", "method": "m", "cells": None, "table": _table(
        group_by=["Fiscal_Year"], measure="Revenue", versus_previous="rate")}
    assert "FY21: 0.00%" in asyncio.run(fallback_answer("q", summary, index, NOTHING, _Planner(plan))).answer
