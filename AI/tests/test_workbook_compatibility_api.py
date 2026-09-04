import pytest
from fastapi.testclient import TestClient

from app.api.workbooks import get_insight_generator
from app.api.workbook_questions import get_question_answer_generator
from app.api.workbook_writebacks import get_writeback_generator
from app.main import app
from app.services.workbook_loading import COMPATIBILITY_ERROR
from tests.support.compatibility_workbook import compatibility_workbook
from tests.support.workbook_api_fixtures import StubInsightGenerator, upload
from tests.test_workbook_questions import StubQuestionGenerator
from tests.test_workbook_writebacks import StubWritebackGenerator


@pytest.fixture
def stub_generators():
    app.dependency_overrides[get_insight_generator] = StubInsightGenerator
    app.dependency_overrides[get_question_answer_generator] = StubQuestionGenerator
    app.dependency_overrides[get_writeback_generator] = StubWritebackGenerator
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize("endpoint", ["summary", "insights", "questions", "writeback-proposals"])
def test_compatibility_workbook_works_across_apis_without_live_llm(endpoint, stub_generators) -> None:
    response = TestClient(app).post(
        f"/api/v1/workbooks/{endpoint}",
        files=upload("sales.xlsx", compatibility_workbook()),
        data={"question": "노트북의 1월 값은 얼마야?", "instruction": "매출현황 B2를 12로 수정해줘"},
    )
    assert response.status_code == 200, response.text
    if endpoint == "questions":
        assert response.json()["status"] == "answered"
    if endpoint == "writeback-proposals":
        assert response.json()["status"] == "ready"


@pytest.mark.parametrize("endpoint", ["summary", "insights", "questions", "writeback-proposals", "writebacks/apply"])
def test_invalid_compatibility_styles_return_400_instead_of_500(endpoint, stub_generators) -> None:
    response = TestClient(app).post(
        f"/api/v1/workbooks/{endpoint}",
        files=upload("sales.xlsx", compatibility_workbook(invalid="missing")),
        data={"question": "값 알려줘", "instruction": "B2 변경", "changes": "[]"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == COMPATIBILITY_ERROR
