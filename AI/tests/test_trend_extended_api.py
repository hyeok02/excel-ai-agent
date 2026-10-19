"""Requested windows and explicit comparisons stay deterministic on upload."""
import pytest

from tests.support.large_workbook_fixtures import offline, parsed, workbook
from tests.test_trend_api import client


def _upload(client, rows, question):
    _, _, content = parsed(workbook({"Records": rows}))
    response = client.post("/api/v1/workbooks/questions", data={"question": question},
                           files={"file": ("arbitrary.xlsx", content)})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("scope", ["2024년", "2024년 1월 이후", "최근 1년"])
def test_upload_checks_only_source_dated_requested_window(client, scope):
    answer = _upload(client, [
        ["Date", "Total Employees"], ["2022-12-31", "=UNAVAILABLE()"],
        ["2024-12-31", 110], ["2024-09-30", 90], ["2024-06-30", 100],
    ], f"{scope} 전체 직원 수의 기간별 추이를 설명해줘")
    assert answer["status"] == "answered", answer
    assert answer["verification"]["level"] == "request_checked"
    assert "반등" in answer["answer"] and "2022-12-31" not in answer["answer"]
    assert "조회" in answer["answer"] or "기준" in answer["answer"]
    assert not any(item["reference"] == "B2" for item in answer["evidence"])


@pytest.mark.parametrize("scale", [1, 10])
def test_upload_compares_explicit_paths_from_current_file_bytes(client, scale):
    answer = _upload(client, [
        ["Date", "Employees", "Contractors"],
        ["2024-01-31", 100 * scale, 20 * scale],
        ["2024-02-29", 80 * scale, 30 * scale],
        ["2024-03-31", 90 * scale, 25 * scale],
    ], "Employees와 Contractors의 기간별 추이를 비교해줘")
    assert answer["status"] in {"answered", "limited"}, answer
    assert "Employees" in answer["answer"] and "Contractors" in answer["answer"]
    assert f"{80 * scale}" in answer["answer"] and f"{30 * scale}" in answer["answer"]
    assert "반등" in answer["answer"] and "하락 전환" in answer["answer"]
    assert not answer["clarification_options"]


def test_upload_will_not_drop_missing_requested_comparison_or_promote_badge(client):
    answer = _upload(client, [
        ["Date", "Employees", "Contractors"],
        ["2024-01-31", 100, 20], ["2024-02-29", 80, None], ["2024-03-31", 90, 25],
    ], "Employees와 Contractors의 기간별 추이를 비교해줘")
    assert answer["status"] == "insufficient_evidence", answer
    assert answer["verification"]["level"] == "unverified"


@pytest.mark.parametrize("labels", [
    ("June Employees", "March Employees"), ("Q1 Employees", "Q2 Employees"),
    ("Last Employees", "Current Employees"),
])
def test_calendar_words_inside_requested_source_labels_are_not_date_filters(client, labels):
    answer = _upload(client, [
        ["Date", *labels], ["2023-01-31", 100, 20],
        ["2024-01-31", 80, 30], ["2025-01-31", 90, 25],
    ], f"{labels[0]}와 {labels[1]}의 기간별 추이를 비교해줘")
    assert answer["status"] == "answered", answer
    assert answer["verification"]["level"] == "request_checked"
    assert answer["answer"].count("3개 관측값") == 2
