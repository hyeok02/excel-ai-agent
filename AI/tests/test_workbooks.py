from io import BytesIO

from fastapi.testclient import TestClient
from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from openpyxl.worksheet.table import Table
from pytest import MonkeyPatch

from app.api.workbooks import get_insight_generator
from app.main import app
from app.services.insight_generator import WorkbookInsight, WorkbookInsightReport

client = TestClient(app)


class StubInsightGenerator:
    async def generate(self, summary: object) -> WorkbookInsightReport:
        return WorkbookInsightReport(
            overview="2개 시트로 구성된 워크북입니다.",
            insights=[
                WorkbookInsight(
                    title="수식 검토 필요",
                    description="매출현황 시트에 합계 수식이 있습니다.",
                    category="formula",
                    severity="info",
                    evidence=["매출현황!D2 = SUM(B2:C2)"],
                    recommendation="합계 범위를 확인하세요.",
                )
            ],
            limitations=["실제 셀 값의 의미는 분석하지 않았습니다."],
        )


def create_workbook_file() -> bytes:
    workbook = Workbook()
    sales_sheet = workbook.active
    sales_sheet.title = "매출현황"
    sales_sheet.append(["상품", "1월", "2월", "합계"])
    sales_sheet.append(["노트북", 10, 20, "=SUM(B2:C2)"])
    sales_sheet.append(["모니터", 5, 15, "=SUM(B3:C3)"])
    sales_sheet.add_table(Table(displayName="SalesTable", ref="A1:D3"))

    chart = BarChart()
    chart.add_data(Reference(sales_sheet, min_col=2, max_col=3, min_row=1, max_row=3))
    sales_sheet.add_chart(chart, "F2")

    workbook.create_sheet("요약")["A1"] = "완료"

    output = BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def test_returns_workbook_summary() -> None:
    response = client.post(
        "/api/v1/workbooks/summary",
        files={
            "file": (
                "sales.xlsx",
                create_workbook_file(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "filename": "sales.xlsx",
        "sheet_count": 2,
        "sheets": [
            {
                "name": "매출현황",
                "rows": 3,
                "columns": 4,
                "formula_count": 2,
                "table_count": 1,
                "chart_count": 1,
                "formulas": [
                    {
                        "cell": "D2",
                        "formula": "=SUM(B2:C2)",
                        "references": ["B2:C2"],
                    },
                    {
                        "cell": "D3",
                        "formula": "=SUM(B3:C3)",
                        "references": ["B3:C3"],
                    },
                ],
                "region_count": 1,
                "regions": [
                    {
                        "start_cell": "A1",
                        "end_cell": "D3",
                        "cell_count": 12,
                    }
                ],
            },
            {
                "name": "요약",
                "rows": 1,
                "columns": 1,
                "formula_count": 0,
                "table_count": 0,
                "chart_count": 0,
                "formulas": [],
                "region_count": 1,
                "regions": [
                    {
                        "start_cell": "A1",
                        "end_cell": "A1",
                        "cell_count": 1,
                    }
                ],
            },
        ],
    }


def test_rejects_unsupported_extension() -> None:
    response = client.post(
        "/api/v1/workbooks/summary",
        files={"file": ("sales.csv", b"name,value", "text/csv")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == ".xlsx 또는 .xlsm 파일만 업로드할 수 있습니다."


def test_rejects_invalid_excel_file() -> None:
    response = client.post(
        "/api/v1/workbooks/summary",
        files={"file": ("sales.xlsx", b"not-an-excel-file")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "올바른 Excel 파일이 아닙니다."


def test_rejects_empty_file() -> None:
    response = client.post(
        "/api/v1/workbooks/summary",
        files={"file": ("sales.xlsx", b"")},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "빈 파일은 업로드할 수 없습니다."


def test_rejects_file_exceeding_size_limit(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.workbooks.MAX_FILE_SIZE_BYTES", 5)

    response = client.post(
        "/api/v1/workbooks/summary",
        files={"file": ("sales.xlsx", b"123456")},
    )

    assert response.status_code == 413
    assert response.json()["detail"] == "파일 크기는 50MB를 초과할 수 없습니다."


def test_returns_structured_workbook_insights() -> None:
    app.dependency_overrides[get_insight_generator] = StubInsightGenerator

    try:
        response = client.post(
            "/api/v1/workbooks/insights",
            files={
                "file": (
                    "sales.xlsx",
                    create_workbook_file(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()
    assert result["workbook"]["filename"] == "sales.xlsx"
    assert result["report"] == {
        "overview": "2개 시트로 구성된 워크북입니다.",
        "insights": [
            {
                "title": "수식 검토 필요",
                "description": "매출현황 시트에 합계 수식이 있습니다.",
                "category": "formula",
                "severity": "info",
                "evidence": ["매출현황!D2 = SUM(B2:C2)"],
                "recommendation": "합계 범위를 확인하세요.",
            }
        ],
        "limitations": ["실제 셀 값의 의미는 분석하지 않았습니다."],
    }


def test_returns_service_unavailable_without_openai_api_key(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr("app.services.insight_generator.load_dotenv", lambda _: False)

    response = client.post(
        "/api/v1/workbooks/insights",
        files={
            "file": (
                "sales.xlsx",
                create_workbook_file(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "OPENAI_API_KEY가 설정되지 않았습니다. AI/.env 파일을 확인하세요."
    )
