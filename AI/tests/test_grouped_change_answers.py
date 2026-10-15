import asyncio
from types import SimpleNamespace

import pytest

from app.agent.query.grouped_change_answers import validated_grouped_change_answer
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.service import WorkbookQuestionService
from app.services.workbook_parsing.models import WorkbookSummary
from tests.support.grouped_change_execution import (
    QUESTION, FailingGenerator, StubExecutor, grouped_execution,
)


@pytest.mark.parametrize(("question", "group"), [
    (QUESTION, "department"),
    ("직무별 직원 수 변화를 시작 값과 마지막 값으로 비교해줘", "role"),
    ("Compare headcount changes by department from first to last values", "department"),
    ("Compare headcount changes for each role", "role"),
    ("항목별 변화를 시작 값과 마지막 값 기준으로 비교해줘", None),
])
def test_service_answers_all_grouped_endpoints_without_model(question, group):
    service = WorkbookQuestionService(
        FailingGenerator(), SimpleNamespace(), StubExecutor(grouped_execution(group)),
    )
    answer = asyncio.run(service.answer(
        question, WorkbookSummary("headcount.xlsx", 0, []),
        WorkbookDataIndex("headcount.xlsx", (), 0, False),
    ))

    assert answer.status is QuestionAnswerStatus.ANSWERED
    assert "2020년 9월 1일부터 2025년 6월 1일까지" in answer.answer
    assert "1,145" in answer.answer and "1,816" in answer.answer
    assert "671" in answer.answer and "58.6%" in answer.answer
    assert "Services" in answer.answer and "100" in answer.answer
    assert {item.reference for item in answer.evidence} == {
        "A2", "A3", "B1", "B2", "B3", "C1", "C2", "C3",
    }


def test_explicit_named_metric_does_not_expand_to_other_departments():
    answer = validated_grouped_change_answer(
        "부서별 R&D 직원 수 변화를 시작 값과 마지막 값으로 비교해줘",
        grouped_execution(), False,
    )

    assert answer is not None and "Research & Development" in answer.answer
    assert "Services" not in answer.answer


@pytest.mark.parametrize("question", [
    "부서별 Supplier A 직원 수 변화를 비교해줘", "직무별 직원 수 변화 비교해줘",
    "부서별 직원 수 평균 변화 비교해줘", "부서별 직원 수 최신값 알려줘",
    "2024년부터 부서별 직원 수 변화 비교해줘",
])
def test_grouped_answers_preserve_question_constraints(question):
    assert validated_grouped_change_answer(question, grouped_execution(), False) is None


@pytest.mark.parametrize("reference", ["B1", "B2", "A2"])
def test_grouped_answers_require_original_headers_values_and_dates(reference):
    execution = grouped_execution()
    cell = next(item for item in execution.steps[0].result.evidence if item.reference == reference)
    cell.value = "unrelated" if reference in {"B1", "A2"} else 999

    assert validated_grouped_change_answer(QUESTION, execution, False) is None


def test_grouped_answer_does_not_claim_single_total_is_departments():
    execution = grouped_execution()
    comparison = execution.steps[0].result.data["time_series_comparison"]
    comparison["metrics"] = [comparison["metrics"][0]]
    comparison["metrics"][0]["header"] = "Total Employees"

    assert validated_grouped_change_answer(QUESTION, execution, False) is None


def test_incomplete_metric_is_not_silently_omitted_from_the_group():
    execution = grouped_execution()
    execution.steps[0].result.data["time_series_comparison"]["metrics"][1].pop("end_value")

    assert validated_grouped_change_answer(QUESTION, execution, False) is None


def test_peak_adjusted_value_is_not_presented_as_the_original_start():
    execution = grouped_execution()
    metric = execution.steps[0].result.data["time_series_comparison"]["metrics"][0]
    metric["start_reference"] = "인원!B4"

    assert validated_grouped_change_answer(QUESTION, execution, False) is None


def test_truncated_grouped_answer_reports_the_scope_limit():
    answer = validated_grouped_change_answer(QUESTION, grouped_execution(), True)

    assert answer is not None and answer.status is QuestionAnswerStatus.LIMITED
    assert answer.limitations
