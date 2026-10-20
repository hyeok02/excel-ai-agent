"""Calendar scopes and derived values through the real upload API, without AI."""
import pytest

from tests.support.large_workbook_fixtures import offline, parsed, workbook
from tests.test_trend_api import client


def ask(client, matrix, question):
    _, _, content = parsed(workbook({"Any Source": matrix}))
    response = client.post("/api/v1/workbooks/questions", data={"question": question},
                           files={"file": ("arbitrary.xlsx", content)})
    assert response.status_code == 200, response.text
    return response.json()


def checked(result):
    assert result["status"] == "answered", result
    assert result["verification"]["level"] == "request_checked", result
    assert {"source_values", "calculation", "request_alignment"} <= set(result["verification"]["checks"])


def test_yoy_quarter_keeps_previous_year_baselines_in_the_original_evidence(client):
    matrix = [["Date", "Total Employees"], ["2023-04-30", 100], ["2023-05-31", 200],
              ["2023-06-30", 100], ["2024-04-30", 120], ["2024-05-31", 220], ["2024-06-30", 90]]
    result = ask(client, matrix, "2024년 2분기 Total Employees 전년 동기 대비 증감률 추이를 설명해줘")
    checked(result)
    assert "2024-04-30: 20%" in result["answer"] and "2024-06-30: -10%" in result["answer"]
    assert "2023-04-30" in result["answer"] and "2024-04-01 ~ 2024-06-30" in result["answer"]
    assert {"B2", "B3", "B4", "B5", "B6", "B7"} <= {cell["reference"] for cell in result["evidence"]}


@pytest.mark.parametrize("category,values", [("서비스", [20, 30, 25]), ("Orchid", [40, 20, 30])])
def test_categorical_share_changes_are_computed_from_complete_population(client, category, values):
    dates = ["2024-01-31", "2024-02-29", "2024-03-31"]
    matrix = [["Date", "부서", "인원"],
              *[[date, group, count] for date, value in zip(dates, values)
                for group, count in [(category, value), ("Other", 100 - value)]]]
    result = ask(client, matrix, f"전체 인원 중 {category} 부서 비중은 늘었어?")
    checked(result)
    assert f"{values[0]}% → {values[-1]}%" in result["answer"]
    assert "2개 범주" in result["answer"]
    original = {f"{column}{row}": value for row, values in enumerate(matrix, 1)
                for column, value in zip("ABC", values)}
    assert all(cell["value"] == original[cell["reference"]] for cell in result["evidence"])


def test_missing_denominator_period_cannot_show_verified_badge(client):
    matrix = [["Date", "부서", "인원"], ["2024-01-31", "서비스", 20], ["2024-01-31", "기타", 80],
              ["2024-02-29", "서비스", 30], ["2024-03-31", "서비스", 25], ["2024-03-31", "기타", 75]]
    result = ask(client, matrix, "전체 인원 중 서비스 부서 비중 추이를 설명해줘")
    assert result["status"] != "answered" and result["verification"]["level"] != "request_checked", result


def test_scenario_grouping_does_not_certify_same_basis_comparison(client):
    matrix = [["Date", "Scenario", "인원"], ["2024-01-31", "Actual", 100],
              ["2024-02-29", "Actual", 110], ["2024-01-31", "Forecast", 120], ["2024-02-29", "Forecast", 150]]
    result = ask(client, matrix, "Scenario별 인원 추이를 비교해줘")
    assert result["status"] != "answered" and result["verification"]["level"] != "request_checked", result
    assert "관측 주기·실적/예상" in " ".join(result["limitations"])


@pytest.mark.parametrize("dates", [
    ["2024A", "2024E", "2025A", "2025E"],
    ["2024-01", "2024-01-01", "2024-02", "2024-02-01"],
])
def test_category_share_does_not_merge_same_timestamp_but_different_period_basis(client, dates):
    matrix = [["Date", "부서", "인원"], *[[date, category, value] for date, category, value in
              zip(dates, ["서비스", "기타", "서비스", "기타"], [20, 80, 30, 70])]]
    result = ask(client, matrix, "전체 인원 중 서비스 부서 비중 추이를 설명해줘")
    assert result["status"] != "answered" and result["verification"]["level"] != "request_checked", result
