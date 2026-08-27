from fastapi.testclient import TestClient

from app.main import app
from tests.support.workbook_api_fixtures import (
    create_workbook_file,
    create_workbook_with_system_sheets,
    upload,
)

client = TestClient(app)


def test_returns_workbook_summary() -> None:
    response = client.post(
        "/api/v1/workbooks/summary", files=upload("sales.xlsx", create_workbook_file())
    )
    assert response.status_code == 200
    result = response.json()
    assert result["filename"] == "sales.xlsx"
    assert result["sheet_count"] == result["total_sheet_count"] == 2
    assert result["excluded_sheet_count"] == 0
    sales = result["sheets"][0]
    assert sales["name"] == "매출현황"
    assert sales["analysis_inclusion"]["decision"] == "include"
    assert sales["sheet_classification"]["role"] == "output"
    assert sales["sheet_classification"]["importance"] in {"high", "critical"}
    assert sales["sheet_classification"]["reasons"]
    assert sales["sheet_classification"]["provenance"]["analyzer"] == (
        "sheet_role_classifier"
    )
    assert sales["analysis_inclusion"]["provenance"]["evidence"][0]["kind"] == (
        "sheet"
    )
    assert sales["formula_count"] == 2
    assert {key: sales["formulas"][0][key] for key in (
        "cell", "formula", "references", "cached_value", "role"
    )} == {
        "cell": "D2",
        "formula": "=SUM(B2:C2)",
        "references": ["B2:C2"],
        "cached_value": None,
        "role": "calculation",
    }
    provenance = sales["formulas"][0]["provenance"]
    assert provenance["analyzer"] == "formula_parser"
    assert provenance["method"] == "rule_based"
    assert provenance["evidence"][0]["sheet_name"] == "매출현황"
    assert provenance["evidence"][0]["reference"] == "D2"
    assert [region["semantic"]["role"] for region in sales["regions"]] == [
        "header",
        "data",
    ]
    assert sales["regions"][0]["semantic"]["reasons"][0]["code"] == (
        "header_style_transition"
    )
    assert sales["regions"][0]["semantic"]["provenance"]["evidence"]
    formula_cell = sales["regions"][1]["preview_rows"][0][3]
    assert formula_cell["address"] == "D2"
    assert formula_cell["formula"] == "=SUM(B2:C2)"
    assert formula_cell["semantic"]["role"] == "formula"
    assert sales["regions"][0]["header_paths"][0] == {
        "column": "A",
        "labels": ["상품"],
    }
    assert sales["tables"][0]["headers"] == ["상품", "1월", "2월", "합계"]
    assert sales["charts"][0]["chart_type"] == "BarChart"
    assert sales["charts"][0]["series"][0]["value_samples"] == ["1월", 10, 5]
    summary = result["sheets"][1]
    assert summary["sheet_classification"]["role"] == "output"
    assert summary["regions"][0]["semantic"]["role"] == "calculation"
    dependencies = result["dependency_summary"]
    assert dependencies["formula_node_count"] == 3
    assert dependencies["edge_count"] == 3
    assert dependencies["cross_sheet_edge_count"] == 1
    assert dependencies["clusters"][0]["edges"][-1] == {
        "source": "매출현황!D2",
        "target": "요약!A2",
        "reference": "매출현황!D2",
        "cross_sheet": True,
    }


def test_excludes_hidden_and_add_in_cache_sheets() -> None:
    response = client.post(
        "/api/v1/workbooks/summary",
        files=upload("system-sheets.xlsx", create_workbook_with_system_sheets()),
    )
    assert response.status_code == 200
    result = response.json()
    assert result["sheet_count"] == 1
    assert result["excluded_sheet_count"] == 3
    assert [sheet["name"] for sheet in result["excluded_sheets"]] == [
        "숨김 계산",
        "__snlofficequeries",
        "CIOHiddenCacheSheet",
    ]
    assert [
        sheet["analysis_inclusion"]["reason_code"]
        for sheet in result["excluded_sheets"]
    ] == ["hidden_worksheet", "addin_cache_worksheet", "system_cache_worksheet"]
