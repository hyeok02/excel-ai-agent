"""Source-first composed operations through the upload route, without any AI."""
from datetime import date, timedelta

import pytest

from tests.support.large_workbook_fixtures import offline, parsed, workbook
from tests.test_trend_api import client


def ask(client, sheets, question):
    _, _, content = parsed(workbook(sheets))
    response = client.post("/api/v1/workbooks/questions", data={"question": question},
                           files={"file": ("arbitrary-same-name.xlsx", content)})
    assert response.status_code == 200, response.text
    return response.json()


def original_evidence(result, sheets):
    from openpyxl.utils import get_column_letter
    original = {(sheet, f"{get_column_letter(column)}{row}"): value
                for sheet, matrix in sheets.items() for row, values in enumerate(matrix, 1)
                for column, value in enumerate(values, 1)}
    assert result["evidence"], result
    for item in result["evidence"]:
        assert item["value"] == original[(item["sheet_name"], item["reference"])], item


def checked(result):
    assert result["status"] == "answered", result
    assert result["verification"]["level"] == "request_checked", result
    assert "request_alignment" in result["verification"]["checks"]


def test_group_growth_upload_keeps_each_groups_own_previous_year(client):
    sheets = {"Measurements": [["Date", "지역", "인원"],
              ["2023-01-31", "Alpha", 100], ["2023-01-31", "Beta", 200],
              ["2023-02-28", "Alpha", 200], ["2023-02-28", "Beta", 100],
              ["2024-01-31", "Alpha", 120], ["2024-01-31", "Beta", 160],
              ["2024-02-29", "Alpha", 260], ["2024-02-29", "Beta", 150]]}
    result = ask(client, sheets, "2024년 지역별 인원 전년 동기 대비 증감률 추이를 비교해줘")
    checked(result)
    for value in ("Alpha", "Beta", "20%", "30%", "-20%", "50%"):
        assert value in result["answer"], result
    original_evidence(result, sheets)


@pytest.mark.parametrize("other", [10, 100000])
def test_scoped_share_does_not_include_other_locations_in_denominator(client, other):
    matrix = [["Date", "부서", "인원", "사업장"]]
    for day, amount in [("2024-01-31", 20), ("2024-02-29", 30)]:
        matrix += [[day, "Orchid", amount, "서울"], [day, "Cedar", 100 - amount, "서울"],
                   [day, "Orchid", other, "부산"], [day, "Cedar", other, "부산"]]
    sheets = {"Measurements": matrix}
    result = ask(client, sheets, "서울 사업장 내에서 부서별 인원 비중 추이를 보여줘")
    checked(result)
    for value in ("Orchid", "Cedar", "20%", "30%", "80%", "70%"):
        assert value in result["answer"], result
    original_evidence(result, sheets)


def test_daily_to_monthly_sum_upload_uses_all_days_and_exact_month_boundaries(client):
    days = [date(2024, 1, 1) + timedelta(days=n) for n in range(60)]
    sheets = {"Ledger": [["Date", "매출 (KRW)"], *[[day.isoformat(), 10] for day in days]]}
    result = ask(client, sheets, "일별 매출 (KRW)을 월별 합계로 보여줘")
    checked(result)
    assert "310" in result["answer"] and "290" in result["answer"], result
    original_evidence(result, sheets)


def joined_sheets():
    return {"이력": [["Date", "부서코드", "인원"],
            ["2024-01-31", "X01", 100], ["2024-01-31", "X02", 200], ["2024-01-31", "X03", 1000],
            ["2024-02-29", "X01", 120], ["2024-02-29", "X02", 180], ["2024-02-29", "X03", 1100]],
            "부서정보": [["부서코드", "부서", "사업장"],
            ["X01", "Orchid", "서울"], ["X02", "Cedar", "서울"], ["X03", "Willow", "부산"]]}


JOINED = "이력과 부서정보를 부서코드로 연결해서 서울 사업장 부서별 월별 인원 추이를 보여줘"


def test_joined_trend_upload_preserves_detail_population_and_dimension_sources(client):
    sheets = joined_sheets()
    result = ask(client, sheets, JOINED)
    checked(result)
    assert "100명 → 120명" in result["answer"] and "200명 → 180명" in result["answer"], result
    assert "1,100명" not in result["answer"]
    assert {"이력", "부서정보"} <= {item["sheet_name"] for item in result["evidence"]}
    original_evidence(result, sheets)


@pytest.mark.parametrize("damage", ["duplicate_key", "missing_key", "unmatched_key"])
def test_unsafe_join_cannot_receive_request_checked_badge(client, damage):
    sheets = joined_sheets()
    if damage == "duplicate_key":
        sheets["부서정보"].append(["X01", "Different", "서울"])
    elif damage == "missing_key":
        sheets["이력"][1][1] = None
    else:
        sheets["이력"][1][1] = "UNKNOWN"
    result = ask(client, sheets, JOINED)
    assert result["status"] != "answered", result
    assert result["verification"]["level"] != "request_checked", result
