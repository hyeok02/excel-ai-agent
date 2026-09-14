from fastapi.testclient import TestClient

from app.agent.writeback.models import WritebackChangeDraft, WritebackProposalDraft
from app.api.workbook_writebacks import get_writeback_generator
from app.main import app
from tests.support.workbook_api_fixtures import create_workbook_file, upload


class StubWritebackGenerator:
    """모델이 특정 셀을 고르도록 고정한다. 검증기 동작만 확인하기 위한 대역이다."""

    def __init__(self, reference: str, new_value: object) -> None:
        self.reference = reference
        self.new_value = new_value

    async def generate(self, instruction, filename, context):
        return WritebackProposalDraft(
            summary="요청한 셀을 변경합니다.",
            changes=[
                WritebackChangeDraft(
                    sheet_name="매출현황",
                    reference=self.reference,
                    new_value=self.new_value,
                    reason="사용자가 정정 값을 명시했습니다.",
                )
            ],
        )


def propose(reference: str, new_value: object, instruction: str):
    app.dependency_overrides[get_writeback_generator] = lambda: StubWritebackGenerator(
        reference, new_value
    )
    try:
        return TestClient(app).post(
            "/api/v1/workbooks/writeback-proposals",
            data={"instruction": instruction},
            files=upload("sales.xlsx", create_workbook_file()),
        )
    finally:
        app.dependency_overrides.clear()


def test_blocks_change_when_target_cell_holds_a_different_current_value() -> None:
    # B2가 10이고 B3은 5다. 요청은 현재 값을 10이라고 밝혔는데 모델이 B3을 골랐다.
    response = propose("B3", 12, "매출현황 노트북 1월 매출을 10에서 12로 바꿔줘")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["changes"] == []
    assert any("현재 값" in risk for risk in body["risks"])


def test_allows_change_when_target_cell_holds_the_stated_current_value() -> None:
    response = propose("B2", 12, "매출현황 B2를 10에서 12로 바꿔줘")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["changes"][0]["old_value"] == 10
    assert body["changes"][0]["new_value"] == 12


def test_keeps_working_when_the_request_does_not_state_a_current_value() -> None:
    response = propose("B3", 12, "매출현황 B3을 12로 바꿔줘")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["changes"][0]["old_value"] == 5


def test_cell_addresses_are_not_read_as_current_values() -> None:
    # "B2:B20을 12로"의 20은 셀 주소의 일부이지 바꾸기 전 값이 아니다.
    response = propose("B2", 12, "매출현황 B2:B20을 12로 바꿔줘")

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
