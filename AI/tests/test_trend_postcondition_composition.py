"""Joined and calendar-aggregated paths enforce the same computed filter gate."""
import pytest

from app.agent.query.trend_answers import trend_answer
from tests.support.large_workbook_fixtures import parsed, workbook


def ask(sheets, question):
    summary, index, _ = parsed(workbook(sheets))
    return trend_answer(question, summary, index)


@pytest.mark.parametrize("operation", ["월별 인원 기말값", "인원 증감률 추이", "인원 비중 추이", "인원 추이"])
def test_joined_computation_does_not_ignore_directional_postfilter(operation):
    sheets = {"이력": [["Date", "부서코드", "인원"],
                       *[[date, code, value] for date, a, b in
                         [("2024-01-31", 20, 80), ("2024-02-29", 30, 70), ("2024-03-31", 40, 60)]
                         for code, value in (("A", a), ("B", b))]],
              "부서정보": [["부서코드", "부서", "사업장"], ["A", "서비스", "서울"], ["B", "생산", "서울"]]}
    result = ask(sheets, f"이력과 부서정보를 부서코드로 연결해서 서울 사업장 부서별 {operation} 증가하는 부서만")
    assert result.status == "insufficient_evidence", result.model_dump()
    assert result.verification.level != "request_checked"


@pytest.mark.parametrize("suffix", ["증가하는 부서만", "감소한 부서는 제외", "상위 1개만"])
def test_calendar_aggregation_keeps_unimplemented_result_filter_visible(suffix):
    sheets = {"Records": [["Date", "부서", "인원"],
                           *[[date, group, value] for date, a, b in
                             [("2024-01-31", 20, 80), ("2024-02-29", 30, 70)]
                             for group, value in (("A", a), ("B", b))]]}
    result = ask(sheets, f"부서별 월별 인원 기말값 {suffix}")
    assert result.status == "insufficient_evidence", result.model_dump()
    assert result.verification.level != "request_checked"
