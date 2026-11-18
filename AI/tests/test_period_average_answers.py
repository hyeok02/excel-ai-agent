"""One year's monthly values averaged, only when one series answers it."""
from io import BytesIO

from openpyxl import Workbook

from app.agent.query.index import build_workbook_data_index
from app.agent.query.period_average_answers import period_average_answer
from app.services.workbook_parser import parse_workbook
from tests.test_named_series_answers import Names


def _sources(sheets):
    book = Workbook()
    book.remove(book.active)
    for name, values in sheets.items():
        sheet = book.create_sheet(name)
        sheet.append(["Month", "Occupancy rate"])
        for month, value in zip(["January 2024", "February 2024", "March 2024", "January 2025"], values):
            sheet.append([month, value])
    stream = BytesIO()
    book.save(stream)
    return parse_workbook("b.xlsx", stream.getvalue()), build_workbook_data_index("b.xlsx", stream.getvalue())


def _ask(question, sheets):
    summary, index = _sources(sheets)
    return period_average_answer(question, summary, index, Names({"점유율": "Occupancy rate"}))


def test_the_year_months_of_one_series_are_averaged_and_counted():
    answer = _ask("2024년 평균 점유율은?", {"All": [90, 92, 94, 80]})
    assert answer.answer.endswith("2024년 평균은 92입니다 (1월~3월, 월별 값 3개의 단순 평균).")
    assert len(answer.evidence) == 7  # the header, and each month's period and value


def test_two_sheets_stay_unanswered_unless_the_question_names_one():
    sheets = {"All": [90, 92, 94, 80], "Type 1": [91, 93, 95, 81]}
    assert _ask("2024년 평균 점유율은?", sheets) is None
    assert _ask("'Type 1'!A1:B5 범위의 B열 Occupancy rate 기준으로: 2024년 평균 점유율은?", sheets).answer.endswith(
        "2024년 평균은 93입니다 (1월~3월, 월별 값 3개의 단순 평균).")
    assert _ask("2024년 점유율 추이 평균은?", {"All": [90, 92, 94, 80]}) is None
