"""Failed recovery preserves source safety, provider boundaries and fallback."""
from dataclasses import replace

import pytest

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswerDraft
from app.agent.query.quota_errors import QuestionQuotaExhaustedError
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_query_models import TabularQueryPlan
from tests.support.missing_plan_recovery import (
    Fallback, InitialOnly, answer, question_for, revised_for, source,
)
from tests.support.replanning_adversarial import Planner
from tests.tabular_query_fixtures import table_fixture


@pytest.mark.parametrize("failure", [None, "invalid schema", {"tabular_query": "broken"},
                                    QuestionIntent(False, "other", from_model=True),
                                    QuestionIntent(True, "summary", from_model=True),
                                    TimeoutError("private provider secret-token")])
def test_failed_missing_plan_repair_preserves_the_original_fallback(source, failure):
    question = question_for(source, "lookup")
    first = QuestionIntent(False, "other", from_model=True)
    generator = Fallback()
    planner = Planner(first, failure)
    result = answer(question, source["summary"], source["index"], planner, generator)
    expected = answer(question, source["summary"], source["index"], InitialOnly(first), Fallback())

    assert result.model_dump() == expected.model_dump()
    assert planner.questions == [question] and len(planner.repairs) == 1
    assert generator.calls == [question]
    assert result.verification.level != "request_checked"
    assert "plan_replanned" not in result.verification.checks
    assert "secret-token" not in result.answer


@pytest.mark.parametrize("code", ["insufficient_quota", "credit_balance_exhausted", "rate_limit_exceeded"])
def test_missing_plan_retry_provider_errors_respect_the_quota_boundary(source, code):
    class ProviderError(Exception):
        def __init__(self):
            super().__init__("private provider secret-token")
            self.body = {"error": {"code": code, "message": str(self)}}

    question = question_for(source, "lookup")
    planner = Planner(QuestionIntent(False, "other", from_model=True), ProviderError())
    generator = Fallback()
    if code == "rate_limit_exceeded":
        result = answer(question, source["summary"], source["index"], planner, generator)
        assert result.verification.level != "request_checked"
        assert "secret-token" not in result.answer and generator.calls == [question]
    else:
        with pytest.raises(QuestionQuotaExhaustedError) as caught:
            answer(question, source["summary"], source["index"], planner, generator)
        assert "secret-token" not in str(caught.value) and generator.calls == []
    assert planner.questions == [question] and len(planner.repairs) == 1


@pytest.mark.parametrize("change", ["drop_filter", "replace_value", "wrong_statistic", "unknown_table"])
def test_recovery_cannot_rewrite_original_scope_or_operation(source, change):
    plan = source["aggregate"]
    changes = {
        "drop_filter": {"filters": []},
        "replace_value": {"filters": [plan.filters[0].model_copy(update={"value": "Elsewhere"})]},
        "wrong_statistic": {"statistic": "average"},
        "unknown_table": {"table_id": "not-a-source-table"},
    }
    question = question_for(source, "aggregate", 1)
    first = QuestionIntent(False, "other", from_model=True)
    revised = replace(revised_for(source, "aggregate"), tabular_query=plan.model_copy(update=changes[change]))
    planner = Planner(first, revised)
    generator = Fallback()
    result = answer(question, source["summary"], source["index"], planner, generator)
    expected = answer(question, source["summary"], source["index"], InitialOnly(first), Fallback())

    assert result.model_dump() == expected.model_dump()
    assert result.verification.level != "request_checked"
    assert "plan_replanned" not in result.verification.checks
    assert planner.questions == [question] and len(planner.repairs) == 1
    assert generator.calls == [question]


def test_keyword_fallback_without_model_plan_does_not_add_a_model_call(source):
    question = question_for(source, "lookup")
    first = QuestionIntent(False, "other", from_model=False)
    planner = Planner(first, revised_for(source, "lookup"))
    generator = Fallback()
    result = answer(question, source["summary"], source["index"], planner, generator)
    baseline_generator = Fallback()
    expected = answer(question, source["summary"], source["index"], InitialOnly(first), baseline_generator)
    assert planner.repairs == [] and generator.calls == baseline_generator.calls
    assert result.model_dump() == expected.model_dump()
    assert result.verification.level != "request_checked"


def test_generated_source_checked_fallback_is_never_upgraded_by_failed_recovery(source):
    class CitedFallback(Fallback):
        async def generate(self, question, filename, execution_context):
            self.calls.append(question)
            prefix = f"'{source['sheet']}'!"
            return QuestionAnswerDraft(
                answer=f"{source['name']}의 {source['measure']}는 {source['first']}입니다.",
                confidence=0.99,
                evidence=[prefix + source["entity_id"] + str(source["start_row"] + 1),
                          prefix + source["measure_id"] + str(source["start_row"] + 1),
                          prefix + source["measure_id"] + str(source["start_row"])],
            )

    question = question_for(source, "lookup")
    planner = Planner(QuestionIntent(False, "other", from_model=True), None)
    generator = CitedFallback()
    result = answer(question, source["summary"], source["index"], planner, generator)
    assert result.status == "answered" and result.evidence
    assert result.verification.level == "source_checked"
    assert "plan_replanned" not in result.verification.checks
    assert "request_alignment" not in result.verification.checks
    assert len(planner.repairs) == 1 and generator.calls == [question]


@pytest.mark.parametrize("unsafe", ["missing_entity", "interpretation"])
def test_source_absence_and_interpretation_are_not_verified_by_recovery(source, unsafe):
    question = (f"{source['entity']}가 Missing Entity인 {source['measure']}의 값을 부탁해"
                if unsafe == "missing_entity" else
                f"{source['region']}의 {source['measure']} 합계가 이렇게 나온 이유는 뭐야?")
    operation = "lookup" if unsafe == "missing_entity" else "aggregate"
    planner = Planner(QuestionIntent(False, "other", from_model=True), revised_for(source, operation))
    result = answer(question, source["summary"], source["index"], planner, Fallback())
    assert result.verification.level != "request_checked"
    assert "plan_replanned" not in result.verification.checks
    assert len(planner.repairs) <= 1


def test_missing_plan_recovery_cannot_hide_mixed_source_currencies():
    summary, index = table_fixture([(3, 2, [
        ["Account", "Amount", "Currency"], ["Orion", 17, "USD"], ["Vega", 31, "EUR"],
    ])], sheet_name="Currency ledger")
    [table] = build_query_tables(summary)
    plan = TabularQueryPlan(operation="numeric_summary", table_id=table.id,
                            column_ids=["C"], statistic="sum")
    planner = Planner(QuestionIntent(False, "other", from_model=True),
                      QuestionIntent(False, "aggregation", from_model=True, tabular_query=plan))
    result = answer("Amount의 합계를 부탁해", summary, index, planner, Fallback())
    assert result.verification.level != "request_checked"
    assert "plan_replanned" not in result.verification.checks
    assert len(planner.repairs) <= 1
