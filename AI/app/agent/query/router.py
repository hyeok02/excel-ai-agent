from app.agent.planning.models import (
    AgentExecutionPlan,
    AgentPlanStep,
    StepFailurePolicy,
)

STRUCTURE_WORDS = ("시트", "구조", "영역", "입력", "출력", "설명", "중요")
DEPENDENCY_WORDS = ("수식", "계산", "참조", "영향", "연결")
CYCLE_WORDS = ("순환", "무한", "circular")
RISK_WORDS = ("오류", "위험", "깨진", "외부", "하드코딩", "동적", "불일치")


def build_question_plan(question: str) -> AgentExecutionPlan:
    normalized = question.casefold()
    selections: list[tuple[str, str, dict[str, object]]] = [
        ("원본 데이터 검색", "search_workbook_data", {"query": question, "row_limit": 24})
    ]
    if _contains(normalized, STRUCTURE_WORDS):
        selections.append(("시트 의미 구조 확인", "inspect_semantic_structure", {}))
    if _contains(normalized, DEPENDENCY_WORDS):
        selections.append(("수식 참조 관계 추적", "trace_formula_dependencies", {"cluster_limit": 8}))
    if _contains(normalized, CYCLE_WORDS):
        selections.append(("순환 참조 확인", "detect_circular_references", {"cycle_limit": 10}))
    if _contains(normalized, RISK_WORDS):
        selections.append(("수식 위험 확인", "assess_formula_risks", {"finding_limit": 30}))
    steps = [_step(index, title, tool, arguments, question) for index, (title, tool, arguments) in enumerate(selections, 1)]
    return AgentExecutionPlan(
        user_intent=question,
        objective="사용자 질문을 원본 Excel 근거로 답변합니다.",
        user_value="원본 시트를 직접 탐색하지 않고 관련 셀과 결론을 함께 확인합니다.",
        expected_deliverable="질문에 대한 답변과 검증 가능한 시트·셀 근거",
        steps=steps,
        success_criteria=["답변에 실제 원본 셀 또는 수식 근거가 포함되어야 합니다."],
        limitations=["도구로 확인되지 않은 내용은 답변하지 않습니다."],
    )


def _step(
    index: int, title: str, tool_name: str, arguments: dict[str, object], question: str
) -> AgentPlanStep:
    return AgentPlanStep(
        id=f"step_{index}",
        title=title,
        tool_name=tool_name,
        arguments=arguments,
        purpose=f"'{question}' 질문에 필요한 근거를 확인합니다.",
        rationale="질문과 직접 관련된 원본 근거를 확보하기 위해 필요합니다.",
        expected_output="답변 작성에 사용할 구조화된 데이터와 셀 근거",
        evidence_required=["원본 시트와 셀 또는 범위"],
        on_failure=StepFailurePolicy.CONTINUE,
    )


def _contains(question: str, words: tuple[str, ...]) -> bool:
    return any(word in question for word in words)
