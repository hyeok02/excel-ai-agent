from fastapi.testclient import TestClient

from app.api.workbook_questions import get_question_answer_generator
from app.main import app
from app.services.insights.models import InsightGenerationError
from tests.support.workbook_api_fixtures import create_workbook_file, upload


class FailingQuestionGenerator:
    async def generate(self, question, filename, execution_context):
        raise InsightGenerationError("Excel 질문에 대한 답변을 생성하지 못했습니다.")


def test_returns_bad_gateway_when_model_generation_fails() -> None:
    app.dependency_overrides[get_question_answer_generator] = FailingQuestionGenerator
    try:
        response = TestClient(app).post(
            "/api/v1/workbooks/questions",
            data={"question": "노트북의 1월 값은 얼마야?"},
            files=upload("sales.xlsx", create_workbook_file()),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert response.json()["detail"] == "Excel 질문에 대한 답변을 생성하지 못했습니다."
