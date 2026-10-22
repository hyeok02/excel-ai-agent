"""Real parsed sources, complete indices, and fail-closed offline service routing."""
import asyncio

from openpyxl import Workbook
import pytest

from app.agent import create_default_tool_registry
from app.agent.query.service import WorkbookQuestionService
from tests.support.large_workbook_fixtures import ForbiddenExternalCall, NoGeneratedAnswer, parsed

QUESTION = "전체 기간 중 인원이 제일 많이 감소한 부서는 어디야?"
DATES = [f"2024-0{month}-01" for month in range(1, 6)]


class NoClassifier:
    async def classify(self, *args):
        raise ForbiddenExternalCall("Original-source change ranking must not call a classifier")


def source(first=(100, 200, 120), second=(100, 100, 70), *, layout="wide", copy=None, number_format='0"명"'):
    book = Workbook()
    sheet = book.active
    sheet.title = "Renamed timeline"
    if layout == "wide":
        matrix = [["Date", "Department", "Department"], ["Date", "Alpha", "Beta"],
                  *list(zip(DATES, first, second))[::-1]]
    else:
        matrix = [["Date", "Department", "Headcount"],
                  *[[date, name, value] for name, values in (("Alpha", first), ("Beta", second))
                    for date, value in zip(DATES, values)][::-1]]
    for row in matrix:
        sheet.append(row)
    for row in sheet:
        for cell in row:
            if isinstance(cell.value, (int, float)):
                cell.number_format = number_format
    for name, rows in {
        "Unrelated current totals": [["Company", "Headcount (Latest)"], ["Issuer", 9000]],
        "Peer comparison": [["Company", "Headcount (Latest)"], ["Neighbor", 1]],
    }.items():
        other = book.create_sheet(name)
        for row in rows:
            other.append(row)
    if copy is not None:
        duplicate = book.copy_worksheet(sheet)
        duplicate.title = "Another chart view"
        if copy == "conflict":
            duplicate["B3"] = 500
    summary, index, _ = parsed(book, filename="random-personnel.xlsx")
    return summary, index


def ask(question=QUESTION, **kwargs):
    summary, index = source(**kwargs)
    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry(),
                                      classifier=NoClassifier())
    return asyncio.run(service.answer(question, summary, index))


def checked(answer):
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked", answer.model_dump()
    assert answer.evidence
    assert not answer.clarification_options
    assert "Unrelated current totals" not in {item.sheet_name for item in answer.evidence}


@pytest.mark.parametrize("layout", ["wide", "long"])
def test_ordinary_question_answers_both_period_drop_and_net_without_a_model(layout):
    answer = ask(layout=layout)
    checked(answer)
    assert "Alpha" in answer.answer and "Beta" in answer.answer
    assert "80명" in answer.answer and "30명" in answer.answer
    assert "고점" in answer.answer and "시작" in answer.answer
    assert "2024-02-01" in answer.answer and "2024-03-01" in answer.answer
    primary, net = answer.answer.split("전체 기간 시작", 1)
    assert "Alpha" in primary and "200명 → 120명" in primary
    assert "Beta" in net and "100명 → 70명" in net
    if layout == "wide":
        assert {"B3", "C3", "B4", "C4", "B5", "C5"} <= {cell.reference for cell in answer.evidence}


def test_explicit_first_last_never_changes_the_baseline_to_the_peak():
    answer = ask("전체 기간의 시작값과 마지막값 기준으로 인원이 제일 많이 감소한 부서는 어디야?")
    checked(answer)
    assert "Beta" in answer.answer and "30명" in answer.answer
    assert "100명 → 70명" in answer.answer
    assert "80명 감소" not in answer.answer


@pytest.mark.parametrize("question, winner, magnitude", [
    ("기간 중 고점 대비 이후 저점까지 인원이 가장 많이 감소한 부서는?", "Alpha", "80명"),
    ("고점 대비 마지막 인원이 가장 많이 감소한 부서는?", "Beta", "40명"),
])
def test_rebound_does_not_conflate_maximum_drawdown_and_peak_to_latest(question, winner, magnitude):
    answer = ask(question, first=(100, 200, 120, 180), second=(100, 100, 70, 60))
    checked(answer)
    assert winner in answer.answer and magnitude in answer.answer


def test_adjacent_drop_uses_only_consecutive_observations():
    answer = ask("직전 기간 대비 인원이 가장 많이 감소한 부서는?",
                 first=(100, 200, 150, 120), second=(100, 100, 70, 70))
    checked(answer)
    assert "Alpha" in answer.answer and "50명" in answer.answer
    assert "80명 감소" not in answer.answer


@pytest.mark.parametrize("rate,winner", [(False, "Alpha"), (True, "Beta")])
def test_percentage_order_is_not_absolute_amount_order(rate, winner):
    question = "전체 기간 시작값과 마지막값 기준으로 " + ("인원 감소율이 가장 큰" if rate else "인원이 가장 많이 감소한") + " 부서는?"
    answer = ask(question, first=(1000, 950, 900), second=(100, 80, 70))
    checked(answer)
    assert winner in answer.answer
    assert ("30%" if rate else "100명") in answer.answer


def test_equal_maximum_drop_reports_all_ties():
    answer = ask(first=(100, 200, 120), second=(50, 150, 70))
    checked(answer)
    primary = answer.answer.split("전체 기간 시작")[0]
    assert "Alpha" in primary and "Beta" in primary


def test_identical_chart_copy_does_not_create_false_source_ambiguity():
    answer = ask(copy="identical")
    checked(answer)
    assert "Alpha" in answer.answer and "80명" in answer.answer


def test_period_drop_is_not_misrepresented_as_first_to_last_decline():
    answer = ask(first=(100, 200, 150), second=(50, 70, 100))
    checked(answer)
    assert "Alpha" in answer.answer and "50명" in answer.answer
    assert "감소한 부서가 없습니다" in answer.answer


@pytest.mark.parametrize("kwargs, question", [
    ({"first": (100, None, 120)}, QUESTION),
    ({"copy": "conflict"}, QUESTION),
    ({}, "서울 사업장만 전체 기간 중 인원이 제일 많이 감소한 부서는 어디야?"),
    ({"first": (0, 0, -10)}, "시작값과 마지막값 기준으로 인원 감소율이 가장 큰 부서는?"),
])
def test_unsafe_source_or_unresolved_request_is_not_certified(kwargs, question):
    answer = ask(question, **kwargs)
    assert answer.status != "answered", answer.model_dump()
    assert answer.verification.level != "request_checked", answer.model_dump()
