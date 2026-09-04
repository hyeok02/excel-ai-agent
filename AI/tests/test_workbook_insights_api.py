from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.api.workbooks import get_insight_generator
from app.main import app
from app.services.analysis_strategy import AnalysisDepth
from tests.support.workbook_api_fixtures import (
    StubInsightGenerator,
    create_workbook_file,
    upload,
)

client = TestClient(app)


def test_returns_structured_workbook_insights() -> None:
    generator = StubInsightGenerator()
    app.dependency_overrides[get_insight_generator] = lambda: generator
    try:
        response = client.post(
            "/api/v1/workbooks/insights",
            data={"depth": "PRECISE"},
            files=upload("sales.xlsx", create_workbook_file()),
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert generator.requested_depth == AnalysisDepth.PRECISE
    assert response.json()["report"] == {
        "overview": "매출현황 시트에 합계 수식이 있습니다.",
        "insights": [
            {
                "title": "수식 검토 필요",
                "fact": "매출현황 시트에 합계 수식이 있습니다.",
                "cause": None,
                "impact": "합계 값은 B열과 C열 참조 범위에 의존합니다.",
                "category": "formula",
                "severity": "info",
                "evidence": ["매출현황!D2"],
                "recommendation": "합계 범위를 확인하세요.",
                "confidence": 0.95,
                "validation_status": "verified",
                "validation_reasons": [],
            }
        ],
        "limitations": [],
        "validation": {
            "generated_count": 1,
            "verified_count": 1,
            "limited_count": 0,
            "blocked_count": 0,
            "notices": [],
        },
    }


def test_rejects_unknown_analysis_depth() -> None:
    app.dependency_overrides[get_insight_generator] = StubInsightGenerator
    try:
        response = client.post(
            "/api/v1/workbooks/insights",
            data={"depth": "UNKNOWN"},
            files=upload("sales.xlsx", create_workbook_file()),
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422


def test_returns_service_unavailable_without_openai_api_key(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("app.services.insight_generator.load_dotenv", lambda _: False)
    response = client.post(
        "/api/v1/workbooks/insights",
        files=upload("sales.xlsx", create_workbook_file()),
    )
    assert response.status_code == 503
    assert response.json()["detail"] == (
        "OPENAI_API_KEY가 설정되지 않았습니다. AI/.env 파일을 확인하세요."
    )
