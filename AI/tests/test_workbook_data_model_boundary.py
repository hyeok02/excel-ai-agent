from io import BytesIO
from zipfile import ZipFile

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from app.api.workbook_questions import get_question_answer_generator
from app.api.workbooks import get_insight_generator
from app.main import app
from app.services.workbook_data_model import DATA_MODEL_ONLY_MESSAGE, LEGACY_XLS_MESSAGE
from app.services.workbook_parser import parse_workbook
from app.services.insights.models import WorkbookInsightReport


def model_workbook(rows=None, hidden=False, embedded=True):
    book = Workbook()
    cover = book.active
    cover.title = "Read Me Renamed"
    cover["B2"] = ("This document contains the instructions for opening its accompanying information. "
                   "Please review the workbook data before using it in a report.")
    if rows:
        sheet = book.create_sheet("Observed Records")
        for row in rows:
            sheet.append(row)
        sheet.sheet_state = "hidden" if hidden else "visible"
    stream = BytesIO()
    book.save(stream)
    book.close()
    if not embedded:
        return stream.getvalue()
    target = BytesIO()
    with ZipFile(BytesIO(stream.getvalue())) as source, ZipFile(target, "w") as result:
        for item in source.infolist():
            content = source.read(item.filename)
            if item.filename == "[Content_Types].xml":
                content = content.replace(b"</Types>", (
                    b'<Default Extension="blob" ContentType="application/vnd.openxmlformats-officedocument.model+data"/>'
                    b"</Types>"))
            result.writestr(item, content)
        # The implementation must discover the feature, not this path/name.
        result.writestr("custom/renamed-model.blob", b"not executed or interpreted")
    return target.getvalue()


class NeverGenerate:
    async def generate(self, *args, **kwargs):
        pytest.fail("Unsupported embedded model must not invoke a paid generator")


@pytest.mark.parametrize("endpoint,dependency,data", [
    ("insights", get_insight_generator, {}),
    ("questions", get_question_answer_generator, {"question": "전체 매출은 얼마야?"}),
])
def test_model_only_workbook_is_explained_before_generation(endpoint, dependency, data):
    app.dependency_overrides[dependency] = NeverGenerate
    try:
        response = TestClient(app).post(
            f"/api/v1/workbooks/{endpoint}", data=data,
            files={"file": ("arbitrary-name.xlsx", model_workbook())},
        )
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 422
    assert response.json()["detail"] == DATA_MODEL_ONLY_MESSAGE


def test_summary_remains_readable_with_truthful_capability_warning():
    response = TestClient(app).post("/api/v1/workbooks/summary",
                                    files={"file": ("arbitrary.xlsx", model_workbook())})
    assert response.status_code == 200
    summary = response.json()
    assert summary["embedded_data_model"] is True
    assert summary["data_model_only"] is True
    assert summary["sheet_count"] == 1
    assert summary["limitations"] == [DATA_MODEL_ONLY_MESSAGE]


@pytest.mark.parametrize("rows", [
    [["Product", "Amount"], ["Widget", 12]],
    [["Company", "Region"], ["Example", "East"], ["Other", "West"]],
    [["Category"], ["Alpha"], ["Beta"]],
    [["Description"], ["Customer feedback recorded as an intentionally long free-text record. " * 2],
     ["Another customer feedback record with its full original wording retained. " * 2]],
    [["Formula"], ["=1+2"]],
])
def test_real_worksheet_data_alongside_model_is_not_blocked(rows):
    summary = parse_workbook("mixed.xlsx", model_workbook(rows))
    assert summary.embedded_data_model is True
    assert summary.data_model_only is False
    assert summary.limitations and "셀 데이터만" in summary.limitations[0]


def test_mixed_workbook_insight_limit_is_returned_in_existing_report_contract():
    class Stub:
        async def generate(self, summary, depth):
            return WorkbookInsightReport(overview="자료를 확인했습니다.", insights=[], limitations=[])

    app.dependency_overrides[get_insight_generator] = Stub
    try:
        response = TestClient(app).post("/api/v1/workbooks/insights", files={"file": (
            "mixed.xlsx", model_workbook([["Product", "Amount"], ["Widget", 12]]),
        )})
    finally:
        app.dependency_overrides.clear()
    assert response.status_code == 200
    assert any("내부 데이터 모델" in limit for limit in response.json()["report"]["limitations"])


def test_hidden_data_becomes_accessible_only_when_explicitly_included():
    content = model_workbook([["Product", "Amount"], ["Widget", 12]], hidden=True)
    hidden = parse_workbook("hidden.xlsx", content)
    assert hidden.data_model_only is True
    included = parse_workbook("hidden.xlsx", content, include_hidden=True)
    assert included.data_model_only is False
    assert "Observed Records" in {sheet.name for sheet in included.sheets}


def test_plain_narrative_workbook_is_not_misreported_as_unsupported_model():
    summary = parse_workbook("plain.xlsx", model_workbook(embedded=False))
    assert summary.embedded_data_model is False
    assert summary.data_model_only is False
    assert not summary.limitations


def test_legacy_xls_explains_real_conversion_not_extension_renaming():
    response = TestClient(app).post("/api/v1/workbooks/summary",
                                    files={"file": ("legacy.xls", b"legacy BIFF bytes")})
    assert response.status_code == 400
    assert response.json()["detail"] == LEGACY_XLS_MESSAGE
