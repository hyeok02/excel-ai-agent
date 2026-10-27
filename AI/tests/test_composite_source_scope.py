"""Model-free multipart conditions bind source fields instead of answer prose."""
import asyncio

from app.agent.query.boolean_source_answers import boolean_source_answer
from app.agent.query.composite_execution import composite_answer
from app.agent.query.question_formula_sources import prepare_formula_sources
from tests.support.large_workbook_fixtures import offline, parsed, workbook


def execute(second):
    summary, index, _ = parsed(workbook({"Records": [
        ["Status", "Amount", "Region"], ["active", 10, "North"],
        ["hold", 20, "North"], ["hold", 30, "South"], ["?", 40, "South"],
    ]}))
    sources = prepare_formula_sources(summary, index)
    calls = []

    async def callback(question, current, **options):
        calls.append(question)
        assert options["intent_override"] is None
        return boolean_source_answer(question, current.summary, current.index)

    question = "Status가 active 또는 hold인 행 수; " + second
    return asyncio.run(composite_answer(question, sources, None, callback)), calls


def test_two_explicit_or_conditions_execute_without_a_composite_model():
    answer, calls = execute("Status가 active 또는 ?인 행 수")
    assert len(calls) == 2
    assert answer.status == "answered" and answer.verification.level == "request_checked", answer.model_dump()
    assert "3건" in answer.answer and "2건" in answer.answer
    assert "compound_parts_2" in answer.verification.checks


def test_missing_local_condition_is_still_ambiguous_without_a_model():
    answer, calls = execute("Amount 평균")
    assert len(calls) == 1
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert any("적용되는지" in item for item in answer.limitations)


def test_another_source_field_does_not_prove_the_first_condition_was_repeated():
    answer, calls = execute("Region이 North 또는 South인 행 수")
    assert len(calls) == 1
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert any("적용되는지" in item for item in answer.limitations)
