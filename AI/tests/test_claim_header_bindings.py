from dataclasses import replace

from app.agent import AgentToolContext, create_default_tool_registry
from app.agent.execution import AgentToolExecutor
from app.agent.query.answer_validation import validate_answer
from app.agent.query.claim_header_bindings import source_header_bindings
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.models import QuestionAnswerDraft
from app.agent.query.router import build_question_plan
from tests.tabular_query_fixtures import table_fixture


def fixture():
    return table_fixture([(1, 1, [
        ["장비", "네트워크 안정", "사유"], ["Unit-A", "x", "점검 대기"],
        ["Unit-B", "o", "점검 완료"],
    ])], "점검")


def test_real_search_tool_supplies_verified_header_mapping_for_generated_claims():
    summary, index = fixture()
    question = "왜 Unit-A의 네트워크 안정이 x야?"
    execution = AgentToolExecutor().execute(
        build_question_plan(question), AgentToolContext(summary, index, question, QuestionIntent(False)),
        create_default_tool_registry(),
    )
    mapping = execution.steps[0].result.data["source_header_bindings"]
    assert mapping["점검!b2"] == "점검!b1"
    draft = QuestionAnswerDraft(answer="임의 해석은 표시하지 않는다", confidence=0.9, claims=[{
        "kind": "cell_value", "value_reference": "점검!B2", "subject_reference": "점검!A2",
        "property_reference": "점검!B1",
    }, {"kind": "unknown"}])
    result = validate_answer(question, draft, execution, False)
    assert result.status == "limited"
    assert "‘x’" in result.answer and "‘Unit-A’" in result.answer
    assert "claim_semantics" in result.verification.checks
    assert any("원인" in note for note in result.limitations)


def test_mapping_cannot_use_values_different_from_the_current_index():
    summary, index = fixture()
    cells = {cell.address: cell for row in index.rows for cell in row.cells}
    wrong = replace(cells["B2"].evidence(), value="o")
    assert source_header_bindings(summary, index, [wrong]) == {}


def test_header_must_be_present_and_identical_in_the_current_index():
    summary, index = fixture()
    modified = replace(index, rows=tuple(
        replace(row, cells=tuple(replace(cell, value="다른 헤더") if cell.address == "B1" else cell
                                 for cell in row.cells)) for row in index.rows
    ))
    evidence = [cell.evidence() for row in modified.rows for cell in row.cells]
    mapping = source_header_bindings(summary, modified, evidence)
    assert "점검!b2" not in mapping


def test_only_current_tool_evidence_can_receive_a_binding():
    summary, index = fixture()
    first = next(cell for row in index.rows for cell in row.cells if cell.address == "B2")
    mapping = source_header_bindings(summary, index, [first.evidence()])
    assert mapping == {"점검!b2": "점검!b1"}
