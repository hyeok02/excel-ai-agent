from fastapi.testclient import TestClient

from app.agent import AgentToolContext, create_default_tool_registry
from app.agent.query import QuestionAnswerDraft, build_workbook_data_index
from app.agent.query.index import IndexedCell, IndexedRow
from app.agent.query.router import build_question_plan
from app.agent.tools.workbook_data import _search_rows
from app.api.workbook_questions import get_question_answer_generator
from app.main import app
from app.services.workbook_parser import parse_workbook
from tests.support.workbook_api_fixtures import create_workbook_file, upload

client = TestClient(app)


class StubQuestionGenerator:
    def __init__(
        self, evidence: list[str] | None = None, answer: str = "노트북의 1월 값은 10입니다."
    ) -> None:
        self.evidence = evidence or ["매출현황!B2"]
        self.answer = answer
        self.context: dict[str, object] = {}

    async def generate(self, question, filename, execution_context) -> QuestionAnswerDraft:
        self.context = execution_context
        return QuestionAnswerDraft(
            answer=self.answer,
            evidence=self.evidence,
            confidence=0.94,
            limitations=[],
        )


def test_answers_question_with_verified_source_cell() -> None:
    generator = StubQuestionGenerator()
    app.dependency_overrides[get_question_answer_generator] = lambda: generator
    try:
        response = client.post(
            "/api/v1/workbooks/questions",
            data={"question": "노트북의 1월 값은 얼마야?"},
            files=upload("sales.xlsx", create_workbook_file()),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["answer"] == "노트북의 1월 값은 10입니다."
    assert body["selected_tools"] == ["search_workbook_data"]
    assert body["evidence"][0]["sheet_name"] == "매출현황"
    assert body["evidence"][0]["reference"] == "B2"
    assert body["evidence"][0]["value"] == 10
    assert generator.context["steps"][0]["tool_name"] == "search_workbook_data"
    assert "rows" not in generator.context["steps"][0]["data"]


def test_blocks_answer_when_model_cites_unknown_cell() -> None:
    generator = StubQuestionGenerator(["매출현황!Z999"])
    app.dependency_overrides[get_question_answer_generator] = lambda: generator
    try:
        response = client.post(
            "/api/v1/workbooks/questions",
            data={"question": "노트북의 1월 값은 얼마야?"},
            files=upload("sales.xlsx", create_workbook_file()),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["evidence"] == []
    assert response.json()["confidence"] == 0


def test_blocks_answer_when_number_does_not_match_cited_cell() -> None:
    generator = StubQuestionGenerator(answer="노트북의 1월 값은 999입니다.")
    app.dependency_overrides[get_question_answer_generator] = lambda: generator
    try:
        response = client.post(
            "/api/v1/workbooks/questions",
            data={"question": "노트북의 1월 값은 얼마야?"},
            files=upload("sales.xlsx", create_workbook_file()),
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_evidence"
    assert response.json()["confidence"] == 0
    assert "999" not in response.json()["answer"]


def test_data_search_tool_returns_question_related_rows_and_cells() -> None:
    content = create_workbook_file()
    summary = parse_workbook("sales.xlsx", content)
    index = build_workbook_data_index("sales.xlsx", content, {"매출현황", "요약"})

    result = create_default_tool_registry().execute(
        "search_workbook_data",
        AgentToolContext(summary, index),
        {"query": "노트북의 1월 값", "row_limit": 10},
    )

    references = {
        f"{item.sheet_name}!{item.reference}" for item in result.evidence
    }
    assert "매출현황!B2" in references
    assert result.data["returned_row_count"] > 0
    result_cells = result.data["rows"][1]["cells"]
    assert any(cell["header"] == "1월" for cell in result_cells)


def test_question_router_selects_formula_tools_from_intent() -> None:
    plan = build_question_plan("깨진 외부 수식의 참조 영향과 순환 위험을 알려줘")

    assert [step.tool_name for step in plan.steps] == [
        "search_workbook_data",
        "trace_formula_dependencies",
        "detect_circular_references",
        "assess_formula_risks",
    ]


def test_korean_business_question_prioritizes_semantically_matching_sheet() -> None:
    rows = (
        _row("Transaction_KeyDev_Details", 69, "Riot Games investment in 2024"),
        _row("Detailed_Headcount_Analytics", 107, "Department Total Employees"),
        _row("Detailed_Headcount_Analytics", 108, "2024-12-01 5428"),
    )

    result = _search_rows(
        rows,
        "Riot Games의 직원 수는 2024년 12월 이후 부문별로 어떻게 변했어?",
        10,
    )

    assert [row.sheet_name for row in result[:2]] == [
        "Detailed_Headcount_Analytics",
        "Detailed_Headcount_Analytics",
    ]


def _row(sheet_name: str, row_number: int, value: str) -> IndexedRow:
    return IndexedRow(
        sheet_name,
        row_number,
        (IndexedCell(sheet_name, f"A{row_number}", value, None),),
    )
