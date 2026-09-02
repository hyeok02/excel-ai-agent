from fastapi.testclient import TestClient

import pytest

from app.agent.query import QuestionAnswerDraft
from app.agent.query.question_validation import unclear_draft_answer, vague_question_answer
from app.api.workbook_questions import get_question_answer_generator
from app.main import app
from tests.support.workbook_api_fixtures import create_workbook_file, upload

client = TestClient(app)


class UnexpectedGenerator:
    def __init__(self) -> None:
        self.called = False

    async def generate(self, question, filename, execution_context) -> QuestionAnswerDraft:
        self.called = True
        raise AssertionError("모호한 질문은 Agent를 실행하면 안 됩니다.")


@pytest.mark.parametrize("question", ["ㅇㅇ", "ㄴㅇㅁ레버저ㅏㅎ", "테스트", "hello"])
def test_vague_question_requests_clarification_without_running_agent(question) -> None:
    generator = UnexpectedGenerator()
    app.dependency_overrides[get_question_answer_generator] = lambda: generator
    try:
        response = client.post(
            "/api/v1/workbooks/questions",
            data={"question": question},
            files=upload("sales.xlsx", create_workbook_file()),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "insufficient_evidence"
    assert "질문이 구체적이지 않아" in body["answer"]
    assert body["selected_tools"] == []
    assert generator.called is False


def test_specific_question_passes_validation() -> None:
    assert vague_question_answer("2025년 직원 수 변화와 근거 셀을 알려줘") is None
    assert vague_question_answer("B2 값은 얼마야?") is None


def test_unclear_model_draft_discards_workbook_facts_and_evidence() -> None:
    draft = QuestionAnswerDraft(
        answer="질문의 의미를 파악할 수 없어 구체적인 분석이나 설명을 제공할 수 없습니다.",
        evidence=["Chart_Data!P17"],
        confidence=0.5,
    )
    answer = unclear_draft_answer("알 수 없는 문장", draft)

    assert answer is not None
    assert "질문이 구체적이지 않아" in answer.answer
    assert answer.evidence == []
    assert answer.confidence == 0


def _sales_index():
    from app.agent.query import build_workbook_data_index

    return build_workbook_data_index("sales.xlsx", create_workbook_file())


def test_accepts_a_term_that_only_the_uploaded_workbook_defines() -> None:
    """용어집에 없던 단어라도 워크북 안에 있으면 구체적인 질문으로 본다."""
    assert vague_question_answer("노트북", _sales_index()) is None


def test_rejects_a_business_term_absent_from_the_uploaded_workbook() -> None:
    """반대로 워크북에 없는 업종 명사는 통과시키지 않는다."""
    assert vague_question_answer("투자", _sales_index()) is not None
