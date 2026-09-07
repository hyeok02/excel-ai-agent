from fastapi.testclient import TestClient

from app.agent import AgentExecutionPlan, AgentPlanStep
from app.main import app
from tests.support.workbook_api_fixtures import create_workbook_file, upload

client = TestClient(app)


def _semantic_plan() -> AgentExecutionPlan:
    return AgentExecutionPlan(
        user_intent="핵심 업무 시트를 알려줘",
        objective="분석 대상 시트와 제외 사유를 확인합니다.",
        user_value="원본의 모든 시트를 열지 않고 핵심 영역을 찾습니다.",
        expected_deliverable="시트 역할과 영역 근거를 포함한 구조 분석",
        steps=[
            AgentPlanStep(
                id="step_1",
                title="의미 구조 확인",
                tool_name="inspect_semantic_structure",
                purpose="업무 시트와 제외 영역을 구분합니다.",
                rationale="분석할 범위를 먼저 확정해야 합니다.",
                expected_output="업무 시트와 영역별 역할",
                evidence_required=["시트 역할과 포함·제외 근거"],
            )
        ],
        success_criteria=["시트별 역할 판단 근거가 포함되어야 합니다."],
    )


def _search_plan() -> AgentExecutionPlan:
    return AgentExecutionPlan(
        user_intent="노트북의 1월 값을 알려줘",
        objective="질문과 관련된 원본 셀 값을 확인합니다.",
        user_value="원본 Excel을 열지 않고 값을 확인합니다.",
        expected_deliverable="질문과 관련된 값과 원본 셀 근거",
        steps=[
            AgentPlanStep(
                id="step_1",
                title="원본 데이터 검색",
                tool_name="search_workbook_data",
                arguments={"query": "노트북의 1월 값", "row_limit": 10},
                purpose="질문과 관련된 원본 셀을 찾습니다.",
                rationale="답변을 검증할 원본 값이 필요합니다.",
                expected_output="관련 셀 값과 셀 주소",
                evidence_required=["원본 시트와 셀 주소"],
            )
        ],
        success_criteria=["관련 셀 값과 주소가 반환되어야 합니다."],
    )


def test_executes_structured_plan_against_uploaded_workbook() -> None:
    response = client.post(
        "/api/v1/agent/executions",
        data={"plan": _semantic_plan().model_dump_json()},
        files=upload("sales.xlsx", create_workbook_file()),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "succeeded"
    assert body["steps"][0]["status"] == "succeeded"
    assert body["steps"][0]["result"]["data"]["sheets"]


def test_executes_workbook_search_with_source_evidence() -> None:
    response = client.post(
        "/api/v1/agent/executions",
        data={"plan": _search_plan().model_dump_json()},
        files=upload("sales.xlsx", create_workbook_file()),
    )

    assert response.status_code == 200
    body = response.json()
    step = body["steps"][0]
    assert body["status"] == "succeeded"
    assert step["status"] == "succeeded"
    assert any(
        item["sheet_name"] == "매출현황"
        and item["reference"] == "B2"
        and item["value"] == 10
        for item in step["result"]["evidence"]
    )


def test_rejects_invalid_or_unregistered_plan() -> None:
    invalid = _semantic_plan().model_copy(deep=True)
    invalid.steps[0].tool_name = "invented_tool"
    response = client.post(
        "/api/v1/agent/executions",
        data={"plan": invalid.model_dump_json()},
        files=upload("sales.xlsx", create_workbook_file()),
    )

    assert response.status_code == 422
    assert "등록되지 않은 도구" in response.json()["detail"]
