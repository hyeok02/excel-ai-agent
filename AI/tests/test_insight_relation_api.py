"""Exercise source relations through upload, parsing, verification and the API."""
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.api.workbooks import get_insight_generator
from app.main import app
from app.services.insights.models import WorkbookInsight, WorkbookInsightReport
from tests.support.workbook_api_fixtures import upload


def insights(rows, fact, evidence="실적!A1:B3", title="매출"):
    class Generator:
        async def generate(self, summary, depth):
            return WorkbookInsightReport(
                overview=fact,
                insights=[WorkbookInsight(
                    title=title, fact=fact, category="summary", severity="info",
                    evidence=[evidence], confidence=0.95,
                )],
            )

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "실적"
    for row in rows:
        sheet.append(row)
    output = BytesIO()
    workbook.save(output)
    workbook.close()
    app.dependency_overrides[get_insight_generator] = Generator
    try:
        response = TestClient(app).post(
            "/api/v1/workbooks/insights",
            files=upload("arbitrary.xlsx", output.getvalue()),
        )
    finally:
        app.dependency_overrides.pop(get_insight_generator, None)
    assert response.status_code == 200
    return response.json()["report"]


@pytest.mark.parametrize(("rows", "evidence"), [
    ([["항목", "값"], ["매출", 100], ["비용", 50]], "실적!A1:B3"),
    ([["매출", "비용"], [100, 50]], "실적!A1:B2"),
    ([["매출", 100, "비용", 50]], "실적!A1:D1"),
])
def test_api_rejects_a_value_borrowed_from_another_metric(rows, evidence):
    fact = "매출은 50입니다."
    report = insights(rows, fact, evidence)
    assert fact not in report["overview"]
    assert not any(item["fact"] == fact for item in report["insights"])
    assert report["validation"]["blocked_count"] >= 1


@pytest.mark.parametrize("fact", [
    "매출은 증가했습니다.", "매출은 감소했습니다.", "매출은 가장 큽니다.",
])
def test_api_rejects_comparison_claims_without_comparison_data(fact):
    report = insights([["항목", "값"], ["매출", 100]], fact, "실적!A1:B2")
    assert fact not in report["overview"]
    assert not any(item["fact"] == fact for item in report["insights"])
    assert report["validation"]["blocked_count"] >= 1


@pytest.mark.parametrize(("rows", "evidence"), [
    ([["항목", "값"], ["매출", 100], ["비용", 50]], "실적!A1:B3"),
    ([["매출", "비용"], [100, 50]], "실적!A1:B2"),
    ([["매출", 100, "비용", 50]], "실적!A1:D1"),
])
@pytest.mark.parametrize(("fact", "title"), [
    ("매출은 100입니다.", "매출"),
    ("비용은 50입니다.", "비용"),
    ("매출은 100이고 비용은 50입니다.", "실적"),
])
def test_api_preserves_correct_metric_value_relationships(rows, evidence, fact, title):
    report = insights(rows, fact, evidence, title)
    assert any(item["fact"] == fact and item["validation_status"] == "verified"
               for item in report["insights"])
    assert report["validation"]["blocked_count"] == 0


@pytest.mark.parametrize(("fact", "title", "valid"), [
    ("매출은 감소했습니다.", "매출", True),
    ("비용은 증가했습니다.", "비용", True),
    ("매출은 증가했습니다.", "매출", False),
    ("비용은 감소했습니다.", "비용", False),
])
def test_api_binds_direction_to_the_correct_metric(fact, title, valid):
    rows = [["날짜", "매출", "비용"],
            ["2024-01-01", 100, 50], ["2024-02-01", 80, 60]]
    report = insights(rows, fact, "실적!A1:C3", title)
    retained = any(item["fact"] == fact and item["validation_status"] == "verified"
                   for item in report["insights"])
    assert retained is valid
    if not valid:
        assert fact not in report["overview"]
        assert report["validation"]["blocked_count"] >= 1


@pytest.mark.parametrize(("fact", "valid"), [
    ("매출은 50이고 증가했습니다.", False),
    ("매출은 2025년 100에서 2024년 150으로 증가했습니다.", False),
    ("매출은 150 증가했습니다.", False),
    ("매출은 100에서 150으로 150 증가했습니다.", False),
    ("매출은 150이고 증가했습니다.", True),
    ("매출은 2024년 100에서 2025년 150으로 증가했습니다.", True),
    ("매출은 50 증가했습니다.", True),
])
def test_api_does_not_confuse_values_dates_and_change_amounts(fact, valid):
    rows = [["날짜", "매출", "비용"],
            ["2024-01-01", 100, 25], ["2025-01-01", 150, 50]]
    report = insights(rows, fact, "실적!A1:C3")
    retained = any(item["fact"] == fact and item["validation_status"] == "verified"
                   for item in report["insights"])
    assert retained is valid
    if not valid:
        assert fact not in report["overview"]
        assert report["validation"]["blocked_count"] >= 1


@pytest.mark.parametrize(("revenue", "cost"), [
    ("$100", "$50"), ("100원", "50원"), ("100 명", "50 명"),
])
@pytest.mark.parametrize(("fact", "valid"), [
    ("매출은 100입니다.", True), ("매출은 50입니다.", False),
])
def test_api_preserves_bindings_for_numbers_stored_as_text(revenue, cost, fact, valid):
    report = insights([["항목", "값"], ["매출", revenue], ["비용", cost]], fact)
    retained = any(item["fact"] == fact and item["validation_status"] == "verified"
                   for item in report["insights"])
    assert retained is valid
