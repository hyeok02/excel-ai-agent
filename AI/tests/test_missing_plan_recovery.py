"""Recover model plan omissions without replacing already valid answers."""
import pytest

from app.agent.query.intent_models import QuestionIntent, QuestionIntentDraft
from tests.support.missing_plan_recovery import (
    Fallback, InitialOnly, answer, question_for, revised_for, source,
)
from tests.support.replanning_adversarial import Planner


@pytest.mark.parametrize("first_kind,operation,wording", [
    (kind, operation, wording)
    for kind in ("other", "aggregation", "cell_lookup")
    for operation in ("aggregate", "lookup")
    for wording in (0, 1, 2)
    if not (kind == "cell_lookup" and operation == "lookup" and wording in (0, 2))
])
def test_source_backed_missing_plan_is_recovered_once_before_generation(source, first_kind, operation, wording):
    question = question_for(source, operation, wording)
    planner = Planner(QuestionIntent(False, first_kind, from_model=True), revised_for(source, operation))
    generator = Fallback()
    result = answer(question, source["summary"], source["index"], planner, generator)

    assert result.status == "answered", result.model_dump()
    assert result.verification.level == "request_checked"
    assert {"request_alignment", "plan_replanned"} <= set(result.verification.checks)
    assert result.evidence and {item.sheet_name for item in result.evidence} == {source["sheet"]}
    expected = source["total"] if operation == "aggregate" else source["first"]
    assert str(expected) in result.answer
    assert planner.questions == [question]
    assert len(planner.repairs) == 1 and planner.repairs[0][0] == question
    assert planner.repairs[0][1]["code"] == "missing_query_plan"
    assert generator.calls == []


@pytest.mark.parametrize("wording", [0, 2])
def test_existing_deterministic_lookup_is_preserved_without_unnecessary_repair(source, wording):
    question = question_for(source, "lookup", wording)
    first = QuestionIntent(False, "cell_lookup", from_model=True)
    planner = Planner(first, revised_for(source, "lookup"))
    generator, baseline_generator = Fallback(), Fallback()
    result = answer(question, source["summary"], source["index"], planner, generator)
    expected = answer(question, source["summary"], source["index"], InitialOnly(first), baseline_generator)

    assert result.model_dump() == expected.model_dump()
    assert result.status == "answered" and str(source["first"]) in result.answer
    assert result.evidence and {item.sheet_name for item in result.evidence} == {source["sheet"]}
    assert any(item.value == source["first"] for item in result.evidence)
    assert "plan_replanned" not in result.verification.checks
    assert planner.questions == [question] and planner.repairs == []
    assert generator.calls == baseline_generator.calls == []


@pytest.mark.parametrize("operation,wrong_kind", [("aggregate", "cell_lookup"), ("lookup", "aggregation")])
def test_schema_accepted_but_kind_incompatible_plan_can_be_recovered(source, operation, wrong_kind):
    first = QuestionIntent.from_draft(QuestionIntentDraft(
        scope="specific", kind=wrong_kind, tabular_query=source[operation],
    ))
    assert first.from_model and first.tabular_query is None
    question = question_for(source, operation)
    planner = Planner(first, revised_for(source, operation))
    generator = Fallback()
    result = answer(question, source["summary"], source["index"], planner, generator)
    assert result.status == "answered" and result.verification.level == "request_checked"
    assert {"request_alignment", "plan_replanned"} <= set(result.verification.checks)
    assert len(planner.repairs) == 1 and planner.questions == [question]
    assert generator.calls == []
