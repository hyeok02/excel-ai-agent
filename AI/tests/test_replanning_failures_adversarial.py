"""Bounded repair propagates quota errors without leaking provider diagnostics."""
import pytest

from app.agent.query.quota_errors import QuestionQuotaExhaustedError
from tests.support.replanning_adversarial import Planner, intent, offline, rejected, run
from tests.test_replanning_source_adversarial import source


class ProviderError(Exception):
    def __init__(self, code):
        super().__init__("private provider diagnostic secret-token")
        self.body = {"error": {"code": code, "message": str(self)}}


@pytest.mark.parametrize("code", ["insufficient_quota", "credit_balance_exhausted"])
def test_replan_quota_is_not_hidden_as_ordinary_answer_failure(code):
    summary, index, plan = source()
    planner = Planner(intent(plan.model_copy(update={"table_id": "invalid"})), ProviderError(code))
    with pytest.raises(QuestionQuotaExhaustedError) as caught:
        run("Company가 Alpha Holdings인 Revenue 합계", summary, index, planner)
    assert "secret-token" not in str(caught.value)
    assert len(planner.questions) == len(planner.repairs) == 1


@pytest.mark.parametrize("failure", [
    ProviderError("rate_limit_exceeded"), TimeoutError("secret-token"),
    ValueError("secret-token"), None, {"tabular_query": "bad schema"}, "not a plan",
])
def test_replan_failure_keeps_original_rejection_without_loop_or_provider_details(failure):
    summary, index, plan = source()
    planner = Planner(intent(plan.model_copy(update={"table_id": "invalid"})), failure)
    answer = run("Company가 Alpha Holdings인 Revenue 합계", summary, index, planner)
    rejected(answer)
    assert "secret-token" not in answer.answer
    assert len(planner.questions) == len(planner.repairs) == 1


def test_keyword_only_plan_failure_does_not_create_an_unexpected_model_invocation():
    from dataclasses import replace

    summary, index, plan = source()
    first = replace(intent(plan.model_copy(update={"table_id": "invalid"})), from_model=False)
    planner = Planner(first, intent(plan))
    rejected(run("Company가 Alpha Holdings인 Revenue 합계", summary, index, planner))
    assert planner.repairs == []
