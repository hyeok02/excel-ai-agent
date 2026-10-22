"""Requested concepts and populations cannot be erased as generic grammar."""
import asyncio

import pytest

from app.agent import create_default_tool_registry
from app.agent.query.service import WorkbookQuestionService
from tests.support.large_workbook_fixtures import NoGeneratedAnswer, parsed, workbook
from tests.test_change_ranking_service import ask, NoClassifier, DATES, QUESTION


def not_certified(answer):
    assert answer.status != "answered", answer.model_dump()
    assert answer.verification.level != "request_checked", answer.model_dump()


@pytest.mark.parametrize("layout", ["wide", "long"])
@pytest.mark.parametrize("metric", ["매출", "비용", "금액", "사용량"])
def test_headcount_source_cannot_answer_other_named_or_generic_measures(layout, metric):
    not_certified(ask(f"전체 기간 중 {metric}이 제일 많이 감소한 부서는 어디야?", layout=layout))


@pytest.mark.parametrize("layout", ["wide", "long"])
@pytest.mark.parametrize("qualifier", ["예상", "추정", "서울 사업장"])
def test_scenario_or_population_is_not_an_ignorable_operation_word(layout, qualifier):
    not_certified(ask(f"{qualifier} 인원이 전체 기간 중 제일 많이 감소한 부서는 어디야?", layout=layout))


@pytest.mark.parametrize("layout", ["wide", "long"])
def test_explicit_one_department_cannot_silently_become_an_all_department_ranking(layout):
    not_certified(ask("Alpha 부서만 전체 기간 중 인원이 제일 많이 감소한 부서는 어디야?", layout=layout))


@pytest.mark.parametrize("number_format", ['"USD "0', '0"원"', '0.0%'])
def test_wide_department_values_with_other_known_units_are_not_headcounts(number_format):
    not_certified(ask(number_format=number_format))


def test_equal_values_for_different_companies_are_not_deduplicated_into_one_population():
    sheets = {name: [["Date", "Department", "Headcount", "Company"],
                     *[[date, group, value, company]
                       for group, values in [("Alpha", [100, 200, 120]), ("Beta", [100, 100, 70])]
                       for date, value in zip(DATES, values)]]
              for name, company in [("Current issuer", "Company A"), ("Separate issuer", "Company B")]}
    book = workbook(sheets)
    for sheet in book:
        for row in sheet.iter_rows(min_row=2):
            row[2].number_format = '0"명"'
    summary, index, _ = parsed(book)
    service = WorkbookQuestionService(NoGeneratedAnswer(), create_default_tool_registry(),
                                      classifier=NoClassifier())
    not_certified(asyncio.run(service.answer(QUESTION, summary, index)))
