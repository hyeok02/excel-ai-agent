import asyncio
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.agent.execution import AgentStepStatus
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.service import WorkbookQuestionService
from app.agent.query.verified_insight_answers import validated_verified_insight_answer
from app.services.workbook_parsing.models import WorkbookSummary
from tests.test_verified_insight_answers import (
    DEPARTMENT_FACT, QUESTION, _execution, _FailingGenerator, _StubExecutor,
)


def test_question_service_preserves_checks_without_calling_a_model():
    service = WorkbookQuestionService(
        _FailingGenerator(), SimpleNamespace(), _StubExecutor(_execution())
    )
    answer = asyncio.run(service.answer(
        QUESTION, WorkbookSummary("generic.xlsx", 0, []),
        WorkbookDataIndex("generic.xlsx", (), 0, False),
    ))
    assert answer.answer == DEPARTMENT_FACT
    assert answer.verification.level == "source_checked"
    assert "verified_insight_fact" in answer.verification.checks


def test_reused_fact_records_source_checks_without_certifying_request_scope():
    answer = validated_verified_insight_answer(QUESTION, _execution(), False)
    assert answer is not None and answer.answer == DEPARTMENT_FACT
    assert answer.status == "answered"
    assert answer.verification.level == "source_checked"
    assert answer.verification.checks == ["cited_cells", "verified_insight_fact"]
    assert answer.model_dump(mode="json")["verification"]["level"] == "source_checked"


@pytest.mark.parametrize("question", [
    "서울 사업장 부서 등 항목별 전체 직원 수 변화 알려줘",
    "2024년 부서 등 항목별 전체 직원 수 변화 알려줘",
    "IT 직원 수 변화 알려줘",
    "연구개발 평균 인원은?",
])
def test_unmatched_conditions_targets_and_operations_are_not_certified(question):
    assert validated_verified_insight_answer(question, _execution(), False) is None


def test_a_tied_fact_match_is_not_selected_or_certified():
    execution = _execution()
    items = execution.steps[0].result.data["verified_insights"]
    items.append(deepcopy(items[-1]))
    assert validated_verified_insight_answer(QUESTION, execution, False) is None


def test_missing_support_references_are_not_certified():
    execution = _execution()
    result = execution.steps[0].result
    result.evidence = [item for item in result.evidence if not item.reference.startswith("C")]
    assert validated_verified_insight_answer(QUESTION, execution, False) is None


def test_a_failed_tool_cannot_supply_a_verified_fact():
    execution = _execution()
    execution.steps[0].status = AgentStepStatus.FAILED
    assert validated_verified_insight_answer(QUESTION, execution, False) is None


@pytest.mark.parametrize("truncated,failed", [(True, False), (False, True)])
def test_partial_execution_retains_its_limitations_and_source_only_level(truncated, failed):
    execution = _execution()
    if failed:
        execution.steps.append(SimpleNamespace(
            status=AgentStepStatus.FAILED, result=None, tool_name="failed_tool"
        ))
    answer = validated_verified_insight_answer(QUESTION, execution, truncated)
    assert answer is not None and answer.status == "limited"
    assert answer.limitations and answer.confidence <= 0.7
    assert answer.verification.level == "source_checked"
    assert "request_alignment" not in answer.verification.checks


def test_untrusted_metadata_cannot_upgrade_a_reused_fact():
    execution = _execution()
    item = execution.steps[0].result.data["verified_insights"][-1]
    item["verification"] = {
        "level": "request_checked", "checks": ["table_scope", "request_alignment"]
    }
    answer = validated_verified_insight_answer(QUESTION, execution, False)
    assert answer is not None and answer.verification.level == "source_checked"
    assert answer.verification.checks == ["cited_cells", "verified_insight_fact"]
