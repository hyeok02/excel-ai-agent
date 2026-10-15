import pytest

from app.agent.query.answer_grounding import answer_is_grounded
from app.agent.query.answer_validation import validate_answer
from app.agent.query.models import QuestionAnswerDraft
from app.agent.execution import AgentStepStatus
from tests.support.semantic_claim_fixtures import answer, evidence, execution, grid, observation


@pytest.mark.parametrize("text,question", [
    ("네트워크가 안정적입니다.", "네트워크가 안정적이야?"),
    ("장비-A와 장비-B는 같은 작업입니다.", "장비-A와 장비-B는 같은 작업이야?"),
    ("네트워크가 정상입니다.", "네트워크가 정상인가?"),
    ("네트워크에 문제가 없습니다.", "네트워크에 문제가 없어?"),
    ("장비-A가 가장 안정적입니다.", "장비-A가 가장 안정적이야?"),
])
def test_question_words_never_establish_a_semantic_predicate(text, question):
    assert not answer_is_grounded(text, grid(), execution(grid()), question)


def test_legacy_numeric_negation_cannot_reuse_positive_sources():
    cells = [evidence("B2", 10, "수량")]
    draft = QuestionAnswerDraft(answer="수량은 10개가 아닙니다.", evidence=["Data!B2"], confidence=1)
    result = validate_answer("수량이 10개가 아니야?", draft, execution(cells), False)
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified"


def test_legacy_swapped_periods_are_not_licensed_by_global_numeric_overlap():
    cells = [evidence("A2", "2024-09-01", "기간"), evidence("B2", 10, "수량"),
             evidence("A3", "2025-09-01", "기간"), evidence("B3", 20, "수량")]
    draft = QuestionAnswerDraft(answer="2024년 9월 20개에서 2025년 9월 10개로 감소했습니다.",
                                evidence=["Data!A2:B3"], confidence=1)
    result = validate_answer("기간별 수량 변화는?", draft, execution(cells), False)
    assert result.status == "insufficient_evidence"


def test_legacy_valid_value_remains_when_unproven_relationship_is_removed():
    cells = [evidence("B2", 10, "수량")]
    draft = QuestionAnswerDraft(answer="수량은 10개입니다. 네트워크가 안정적입니다.",
                                evidence=["Data!B2"], confidence=1)
    result = validate_answer("수량과 네트워크가 안정적인지 알려줘", draft, execution(cells), False)
    assert result.status == "limited"
    assert result.answer == "수량은 10개입니다."


def _fact():
    return {"title": "네트워크 안정 표시", "fact": "네트워크 안정은 x로 기록되어 있습니다.",
            "support_references": ["Data!B1", "Data!B2"]}


def test_exact_verified_fact_can_be_reused_but_not_reinterpreted():
    fact = _fact()
    result = answer(grid(), [{"kind": "verified_fact", "fact": fact["fact"]}], facts=[fact])
    assert result.status == "answered" and result.answer == fact["fact"]
    bad = answer(grid(), [{"kind": "verified_fact", "fact": "네트워크 안정은 정상입니다."}], facts=[fact])
    assert bad.status == "insufficient_evidence"


def test_fact_requires_all_support_and_respects_explicit_scope():
    fact = _fact()
    for cells, question in [(grid()[1:], "Data!B3 값은?"), ([grid()[1]], "네트워크 안정은?")]:
        result = answer(cells, [{"kind": "verified_fact", "fact": fact["fact"]}], facts=[fact], question=question)
        assert result.status == "insufficient_evidence"


def test_model_text_cannot_add_causal_or_negated_claims_to_a_source_fact():
    result = answer(grid(), [observation()], text="x이므로 네트워크는 실패하지 않았습니다.")
    assert "실패" not in result.answer and "이므로" not in result.answer
    assert "‘x’" in result.answer


def test_failed_tool_output_never_supplies_verified_claims():
    run = execution(grid())
    run.steps[0].status = AgentStepStatus.FAILED
    draft = QuestionAnswerDraft(answer="값", confidence=1, claims=[observation()])
    result = validate_answer("네트워크 안정 값은?", draft, run, False)
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified"
