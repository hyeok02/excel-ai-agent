"""One period's value of a series read section by section: annual totals first, partial bases never."""
from types import SimpleNamespace

from openpyxl import Workbook

from app.agent.query.index import build_workbook_data_index
from app.agent.query.series_value_answers import series_value_answer
from app.services.workbook_parser import parse_workbook
from tests.test_named_series_answers import Names


def _sources():
    book = Workbook()
    sheet = book.active
    sheet.title = "Gen"
    for row in [["Period", "Coal", "Total"], ["Annual Totals"], [2024, 10, 100], [2025, 12, 110],
                ["Year 2025"], ["January", 1, 9], ["February", 2, 8], ["Year to Date"], [2026, 5, 70], [2025, 4, 60]]:
        sheet.append(row)
    from io import BytesIO
    stream = BytesIO()
    book.save(stream)
    return parse_workbook("g.xlsx", stream.getvalue()), build_workbook_data_index("g.xlsx", stream.getvalue())


def _ask(question):
    summary, index = _sources()
    return series_value_answer(question, summary, index, resolver=Names({"총발전량": "Total", "석탄": "Coal"}))


def test_the_asked_year_is_read_from_the_annual_section():
    answer = _ask("2025년 총발전량은?")
    assert answer.answer.splitlines()[0] == "해석: ‘총발전량’ → Total"
    assert "Annual Totals" in answer.answer and answer.answer.endswith("2025년 값은 110입니다.")
    assert {item.reference for item in answer.evidence} >= {"A4", "C4"}
    assert _ask("2025년 2월 석탄 발전량은?").answer.endswith("2025년 2월 값은 2입니다.")


def test_a_partial_basis_or_another_question_never_answers():
    assert _ask("2026년 총발전량은?") is None  # only a year-to-date row holds 2026
    assert _ask("2025년 총발전량 추이는?") is None
    assert _ask("총발전량은?") is None
