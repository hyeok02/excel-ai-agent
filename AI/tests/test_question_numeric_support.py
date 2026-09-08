from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace

from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.agent.query import QuestionAnswerDraft
from app.agent.query.numeric_support import supported_answer_numbers
from app.api.workbook_questions import get_question_answer_generator
from app.main import app
from app.services.insights.verification.numeric_validation import unmatched_numbers
from tests.support.workbook_api_fixtures import upload

client = TestClient(app)


class TimeSeriesAnswerGenerator:
    async def generate(self, question, filename, execution_context) -> QuestionAnswerDraft:
        return QuestionAnswerDraft(
            answer=(
                "2023년 9월 6,101명에서 2025년 6월 5,417명으로 "
                "684명(11.2%) 감소했습니다."
            ),
            evidence=["직원현황!A2:B2", "직원현황!A3:B3"],
            confidence=0.93,
        )


def test_time_series_answer_accepts_period_and_calculated_change() -> None:
    app.dependency_overrides[get_question_answer_generator] = TimeSeriesAnswerGenerator
    try:
        response = client.post(
            "/api/v1/workbooks/questions",
            data={"question": "Total Employees 직원 수가 줄어들었어?"},
            files=upload("headcount.xlsx", _time_series_workbook()),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert "684명(11.2%) 감소" in body["answer"]
    assert {item["reference"] for item in body["evidence"]} == {
        "A2", "B2", "A3", "B3",
    }


def test_search_scope_limit_does_not_reduce_verified_confidence() -> None:
    app.dependency_overrides[get_question_answer_generator] = TimeSeriesAnswerGenerator
    try:
        response = client.post(
            "/api/v1/workbooks/questions",
            data={"question": "Total Employees 직원 수가 줄어들었어?"},
            files=upload("large-headcount.xlsx", _time_series_workbook(70)),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "limited"
    assert body["confidence"] == 0.93
    assert any("검색 범위에서 제외" in item for item in body["limitations"])


def test_percent_and_rounded_number_match_source_value() -> None:
    assert unmatched_numbers("11.2% 감소", {Decimal("0.112")}) == set()
    assert unmatched_numbers("약 11% 감소", {Decimal("11.211")}) == set()
    assert unmatched_numbers("1.2e3명", {Decimal("1200")}) == set()


def test_does_not_invent_calculations_or_use_header_numbers() -> None:
    evidence = [
        SimpleNamespace(value=10, formula=None, description="1월"),
        SimpleNamespace(value=20, formula=None, description="2월"),
    ]
    candidates = supported_answer_numbers(
        "두 값의 합계와 평균은?", evidence, SimpleNamespace(steps=[])
    )

    assert {Decimal("10"), Decimal("20")} <= candidates
    assert Decimal("8.25") not in candidates
    assert Decimal("15") not in candidates
    assert Decimal("30") not in candidates


def _time_series_workbook(extra_rows: int = 0) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "직원현황"
    extra_headers = [f"Metric {index}" for index in range(1, 699)]
    sheet.append(["Date", "Total Employees", *extra_headers])
    sheet.append(["2023-09-01", 6101, *range(1, 699)])
    sheet.append(["2025-06-01", 5417, *range(2, 700)])
    for row_index in range(extra_rows):
        sheet.append([f"Archive {row_index}", row_index, *range(1, 699)])
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()
