"""Only a completed successful tool may supply source-verification evidence."""
import pytest

from app.agent.execution import AgentStepStatus
from app.agent.query.answer_validation import validate_answer
from app.agent.query.comparison_evidence import available_evidence
from app.agent.query.models import QuestionAnswerDraft
from tests.support.semantic_claim_fixtures import evidence, execution


@pytest.mark.parametrize("status", [AgentStepStatus.FAILED, AgentStepStatus.SKIPPED,
                                    AgentStepStatus.PENDING, AgentStepStatus.RUNNING])
def test_unsuccessful_tool_values_never_enter_common_evidence(status):
    result = execution([evidence("B2", 10, "수량")])
    result.steps[0].status = status
    assert available_evidence(result) == {}


def test_failed_legacy_tool_result_cannot_be_source_checked():
    result = execution([evidence("B2", 10, "수량")])
    result.steps[0].status = AgentStepStatus.FAILED
    draft = QuestionAnswerDraft(answer="수량은 10개입니다.", evidence=["Data!B2"], confidence=1)
    answer = validate_answer("수량은?", draft, result, False)
    assert answer.status == "insufficient_evidence"
    assert answer.verification.level == "unverified"
    assert answer.evidence == []


def test_successful_values_survive_unrelated_failed_tool_without_contamination():
    valid = execution([evidence("B2", 10, "수량")])
    failed = execution([evidence("B2", 999, "wrong quantity"), evidence("C2", 999, "other")])
    failed.steps[0].status = AgentStepStatus.FAILED
    valid.steps.extend(failed.steps)
    available = available_evidence(valid)
    assert list(available) == ["data!B2".casefold()]
    assert next(iter(available.values())).value == 10
