"""Upload-path grouped calculations are deterministic and isolated per workbook."""
import pytest

from tests.support.large_workbook_fixtures import offline, parsed, workbook
from tests.test_grouped_trend_adversarial import DATES, QUESTION, grouped
from tests.test_trend_api import client


def upload(client, matrix, question=QUESTION):
    _, _, content = parsed(workbook({"Records": matrix}))
    response = client.post("/api/v1/workbooks/questions", data={"question": question},
                           files={"file": ("same-name.xlsx", content)})
    assert response.status_code == 200, response.text
    return response.json()


def test_grouped_upload_needs_no_classifier_and_does_not_reuse_same_name_values(client):
    for scale in (1, 10, 1):
        result = upload(client, grouped(scale=scale))
        assert result["status"] == "answered", result
        assert result["verification"]["level"] == "request_checked", result
        assert "서비스" in result["answer"] and "개발" in result["answer"]
        assert f"{100 * scale:,}명 → {90 * scale:,}명" in result["answer"]
        assert result["answer"].count("3개 관측값") == 2


@pytest.mark.parametrize("value", [None, "=EXTERNAL_PROVIDER()"])
def test_upload_missing_group_value_cannot_have_verified_badge(client, value):
    matrix = grouped()
    matrix[3][2] = value
    result = upload(client, matrix)
    assert result["status"] != "answered", result
    assert result["verification"]["level"] != "request_checked", result


def test_upload_explicit_group_aggregate_uses_all_original_rows(client):
    matrix = [["Date", "부서", "인원", "사업장"],
              [DATES[0], "서비스", 100, "서울"], [DATES[0], "서비스", 20, "서울"],
              [DATES[1], "서비스", 130, "서울"], [DATES[1], "서비스", 40, "서울"]]
    result = upload(client, matrix, "서울 사업장만 부서별 인원 합계 추이를 비교해줘")
    assert result["status"] == "answered", result
    assert result["verification"]["level"] == "request_checked", result
    assert "120명 → 170명" in result["answer"]
    assert {"C2", "C3", "C4", "C5"} <= {cell["reference"] for cell in result["evidence"]}
