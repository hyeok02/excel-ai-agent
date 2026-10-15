"""Synthetic report layouts: no customer filenames, names or coordinates."""

from datetime import datetime

import pytest

from app.agent.query.index import IndexedCell, IndexedRow, WorkbookDataIndex
from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.metric_observation_periods import requested_periods
from app.agent.query.metric_scalar_answers import metric_scalar_answer
from app.agent.query.models import QuestionAnswerStatus, QuestionVerificationLevel
from app.agent.query.question_dates import question_date_bounds


def _index(sheets, formats=None, truncated=False):
    rows = []
    formats = formats or {}
    for sheet, cells in sheets.items():
        by_row = {}
        for address, value in cells.items():
            row = int("".join(character for character in address if character.isdigit()))
            by_row.setdefault(row, []).append(IndexedCell(
                sheet, address, value, None, number_format=formats.get((sheet, address), "General"),
            ))
        rows.extend(IndexedRow(sheet, number, tuple(cells)) for number, cells in sorted(by_row.items()))
    return WorkbookDataIndex("arbitrary.xlsx", tuple(rows), sum(len(row.cells) for row in rows), truncated)


def _report():
    return {
        "C2": "Currency", "C3": "USD", "E2": "Magnitude", "E3": "Millions",
        "C6": "Fiscal Year Ending", "F6": "Quarter Ended",
        "B7": "Period Ended", "C7": "2022-09-30", "D7": "2023-09-30",
        "E7": "2024-09-30", "F7": "2024-09-30",
        "B9": "Operating Income", "C9": 400, "D9": 520, "E9": 650, "F9": 180,
    }


def test_explicit_years_select_requested_operands_not_report_endpoints():
    answer = metric_observation_answer(
        "Operating Income은 2023년에서 2024년으로 얼마나 증가했어?", None, _index({"Results": _report()}),
    )
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert "520백만 미국 달러" in answer.answer and "650백만 미국 달러" in answer.answer
    assert "130백만 미국 달러" in answer.answer and "25.0000%" in answer.answer
    refs = {item.reference for item in answer.evidence}
    assert {"D7", "E7", "D9", "E9"} <= refs
    assert "C9" not in refs and "F9" not in refs
    assert answer.verification.level is QuestionVerificationLevel.REQUEST_CHECKED


def test_same_end_date_keeps_annual_and_quarterly_values_distinct():
    answer = metric_observation_answer(
        "2024년 9월 30일 종료 회계연도 Operating Income과 같은 날짜 종료 분기를 구분해줘.",
        None, _index({"Shifted": _report()}),
    )
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert "회계연도 Operating Income: 650" in answer.answer
    assert "분기 Operating Income: 180" in answer.answer
    assert {"C6", "F6", "E9", "F9"} <= {item.reference for item in answer.evidence}


def test_exact_date_without_grain_does_not_choose_between_annual_and_quarter():
    answer = metric_observation_answer(
        "2024년 9월 30일 Operating Income은 얼마야?", None, _index({"Results": _report()}),
    )
    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.verification.level is QuestionVerificationLevel.UNVERIFIED


def test_actual_estimate_headers_are_bound_to_the_correct_column_segments():
    source = {
        "B2": "Currency", "B3": "EUR", "D2": "Magnitude", "D3": "Thousands",
        "E6": "Fiscal Year Ended", "E7": "Actuals", "G7": "LTM", "J7": "Estimates",
        "B8": "Period Ended", "E8": "2030-12-31", "F8": "2031-12-31",
        "G8": "2031-12-31", "J8": "2032-12-31",
        "B10": "Operating Income", "E10": 45, "F10": 60, "G10": 999, "J10": 72,
    }
    answer = metric_observation_answer(
        "2031년 실제 Operating Income과 2032년 예상 Operating Income을 비교해줘.", None,
        _index({"Forecast": source}),
    )
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert "60천 유로" in answer.answer and "72천 유로" in answer.answer
    assert "20.0000%" in answer.answer and "예상치" in answer.answer
    assert "999" not in answer.answer
    assert {"E7", "J7", "F8", "J8"} <= {item.reference for item in answer.evidence}


def test_latest_reads_the_metrics_as_of_column_not_an_unrelated_date():
    source = {
        "B4": "Company Name", "F4": "Headcount (Latest)", "G4": "Headcount As Of",
        "H4": "Transaction Date", "B6": "Aurora Labs, Inc.", "F6": 120,
        "G6": "2031-07-01", "H6": "2035-01-01",
        "B7": "Aurora Labs, Inc.", "F7": 110, "G7": "2031-06-01", "H7": "2040-01-01",
        "B8": "Other Company", "F8": 999, "G8": "2036-07-01", "H8": "2041-01-01",
    }
    answer = metric_observation_answer("Aurora Labs의 최신 직원 수와 기준일은?", None,
                                       _index({"Roster": source}))
    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert "2031년 7월 1일" in answer.answer and "120명" in answer.answer
    assert {"B6", "F6", "G6", "G4"} <= {item.reference for item in answer.evidence}
    assert not ({"H6", "H7", "F8"} & {item.reference for item in answer.evidence})


def test_conflicting_latest_values_are_not_verified():
    base = {
        "A1": "Company", "B1": "Headcount", "C1": "Headcount As Of",
        "A2": "Lumen Works", "B2": 20, "C2": "2030-10-01",
        "A3": "Lumen Works", "B3": 25, "C3": "2030-10-01",
    }
    answer = metric_observation_answer("Lumen Works의 최신 Headcount 알려줘", None, _index({"Data": base}))
    assert answer.status is QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
    assert answer.verification.level is QuestionVerificationLevel.UNVERIFIED
