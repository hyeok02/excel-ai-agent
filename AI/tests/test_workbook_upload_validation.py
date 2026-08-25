from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from app.main import app

client = TestClient(app)


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
        "/api/v1/workbooks/summary", files={"file": ("sales.xlsx", b"")}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "빈 파일은 업로드할 수 없습니다."


def test_rejects_file_exceeding_size_limit(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.workbooks.MAX_FILE_SIZE_BYTES", 5)
    response = client.post(
        "/api/v1/workbooks/summary", files={"file": ("sales.xlsx", b"123456")}
    )
    assert response.status_code == 413
    assert response.json()["detail"] == "파일 크기는 50MB를 초과할 수 없습니다."
