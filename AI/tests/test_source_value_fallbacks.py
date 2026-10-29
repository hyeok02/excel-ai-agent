"""A refused or clarified value question is answered only when every source agrees."""
from datetime import datetime
from io import BytesIO

from openpyxl import Workbook

from app.agent.query.index import build_workbook_data_index
from app.agent.query.source_value_answers import source_value_answer
from app.agent.tools.workbook_metric_periods import build_metric_period
from app.services.workbook_parser import parse_workbook

MONTHS = [datetime(2023, month, 1) for month in range(1, 7)]


def _book(sheets):
    book = Workbook()
    book.remove(book.active)
    for name, rows in sheets.items():
        sheet = book.create_sheet(name)
        for row in rows:
            sheet.append(row)
    stream = BytesIO()
    book.save(stream)
    content = stream.getvalue()
    summary = parse_workbook("book.xlsx", content)
    return summary, build_workbook_data_index("book.xlsx", content, {sheet.name for sheet in summary.sheets})


def _headcount(total=(100, 110, 120, 130, 140, 150)):
    return [["Date", "Total Employees", "Engineering"],
            *[[day, value, value // 2] for day, value in zip(MONTHS, total)]]


def test_a_named_month_selects_its_own_row() -> None:
    summary, index = _book({"Headcount": _headcount()})
    answer = source_value_answer("2023년 3월 직원 수는?", summary, index)

    assert answer is not None and "120" in answer.answer and "2023년 3월 1일" in answer.answer
    assert answer.selected_tools == ["source_value_lookup"]
    assert any(item.reference == "B4" for item in answer.evidence)


def test_without_a_period_the_newest_row_of_one_series_is_used() -> None:
    summary, index = _book({"Headcount": _headcount()})
    answer = source_value_answer("Engineering 인원은?", summary, index)

    assert answer is not None and "75" in answer.answer and "2023년 6월 1일" in answer.answer


def test_copies_that_disagree_are_not_settled() -> None:
    summary, index = _book({"Headcount": _headcount(), "Copy": _headcount((100, 110, 120, 130, 140, 151))})

    assert source_value_answer("Total Employees 값은?", summary, index) is None


def test_copies_that_agree_are_answered_once_with_every_place() -> None:
    summary, index = _book({"Headcount": _headcount(), "Copy": _headcount()})
    answer = source_value_answer("Total Employees 값은?", summary, index)

    assert answer is not None and "150" in answer.answer and "2곳" in answer.answer


def test_rows_the_question_cannot_select_block_the_lookup() -> None:
    rows = [["Name", "Department", "Employees"], ["A", "Sales", 10], ["B", "Support", 20], ["C", "R&D", 30]]
    summary, index = _book({"Teams": rows})

    assert source_value_answer("Employees 값은?", summary, index) is None
    assert "20" in source_value_answer("Support Employees 값은?", summary, index).answer


def test_an_average_request_is_never_a_row_whose_name_says_average() -> None:
    rows = [["Owner Name", "Percent Held (%)"], ["Vanguard Group Inc.", 8.6],
            ["SPDR Dow Jones Industrial Average ETF Trust", 0.19], ["BlackRock Inc.", 6.9]]
    summary, index = _book({"Holders": rows})

    assert source_value_answer("Percent Held (%) 평균은?", summary, index) is None
    assert "8.6" in source_value_answer("Vanguard Percent Held (%) 값은?", summary, index).answer


def test_lists_totals_and_trends_are_not_single_lookups() -> None:
    summary, index = _book({"Headcount": _headcount()})

    for question in ("직원 수 합계는?", "직원 수 추이 알려줘", "가장 많은 직원 수는?", "3월 직원 수는?", "최대 직원 수는?"):
        assert source_value_answer(question, summary, index) is None


def test_a_named_field_period_is_not_the_data_period() -> None:
    comparison = {"start_date": "2020-01-01", "end_date": "2025-06-01",
                  "start_reference": "A2", "end_reference": "A67"}

    assert build_metric_period(comparison, "평균 근속 기간은?") is None
    assert build_metric_period(comparison, "계약 기간이 얼마야?") is None
    assert build_metric_period(comparison, "데이터 기간은?")["end_date"] == "2025-06-01"
    assert build_metric_period(comparison, "기간이 어떻게 돼?")["start_date"] == "2020-01-01"
