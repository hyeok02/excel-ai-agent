"""시트 구성 질문에 대한 결정론적 답변.

LLM을 거치지 않고 의미 구조 도구 결과만으로 문장을 만든다. 시트 이름과
역할은 이미 검증된 근거이므로, 답변이 원본과 어긋날 여지가 없다.
"""
from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.comparison_evidence import (
    available_evidence,
    matched_comparison_evidence,
    present_comparison_evidence,
)
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus

STRUCTURE_PHRASES = (
    "어떤 시트",
    "무슨 시트",
    "시트 구성",
    "시트로 구성",
    "시트 구조",
    "시트는 몇",
    "시트가 몇",
    "파일 구조",
    "워크북 구조",
)
ROLE_LABELS = (
    ("output", "분석 결과가 정리된"),
    ("calculation", "값을 계산하는"),
    ("input", "원본 값을 입력하는"),
    ("documentation", "사용 방법을 설명하는"),
)
MAX_NAMES_PER_ROLE = 4
MAX_PRESENTED_EVIDENCE = 24


def is_structure_question(question: str) -> bool:
    normalized = " ".join(question.casefold().split())
    return any(phrase in normalized for phrase in STRUCTURE_PHRASES)


def validated_structure_answer(
    question: str, execution: AgentExecution, index_truncated: bool
) -> QuestionAnswer | None:
    if not is_structure_question(question):
        return None
    step = _structure_step(execution)
    if step is None:
        return None
    sheets = [
        sheet
        for sheet in step.result.data.get("sheets", [])
        if isinstance(sheet, dict) and sheet.get("name")
    ]
    if not sheets:
        return None
    evidence, missing = matched_comparison_evidence(
        _references(step), available_evidence(execution)
    )
    if not evidence or missing:
        return None
    limitations = _limitations(execution, index_truncated)
    return QuestionAnswer(
        question=question,
        answer=_text(sheets, step.result.data.get("excluded_sheets")),
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        confidence=0.7 if limitations else 1.0,
        selected_tools=[item.tool_name for item in execution.steps],
        evidence=[
            present_comparison_evidence(item)
            for item in evidence[:MAX_PRESENTED_EVIDENCE]
        ],
        limitations=limitations,
    )


def _structure_step(execution: AgentExecution):
    for step in execution.steps:
        if (
            step.status is AgentStepStatus.SUCCEEDED
            and step.tool_name == "inspect_semantic_structure"
            and step.result
            and isinstance(step.result.data.get("sheets"), list)
        ):
            return step
    return None


def _references(step) -> list[str]:
    references = [
        f"{item.sheet_name}!{item.reference}"
        for item in step.result.evidence
        if item.reference and item.sheet_name
    ]
    return list(dict.fromkeys(references))[:MAX_PRESENTED_EVIDENCE]


def _text(sheets: list[dict], excluded: object) -> str:
    sentences = [f"이 파일은 시트 {len(sheets)}개로 구성되어 있습니다."]
    sentences.extend(_role_sentences(sheets))
    if isinstance(excluded, list) and excluded:
        sentences.append(f"숨김 시트 {len(excluded)}개는 분석에서 제외했습니다.")
    return " ".join(sentences)


def _role_sentences(sheets: list[dict]) -> list[str]:
    sentences = []
    for role, label in ROLE_LABELS:
        names = [_name(sheet) for sheet in sheets if sheet.get("role") == role]
        if names:
            sentences.append(f"{label} 시트는 {_names(names)}입니다.")
    return sentences


def _name(sheet: dict) -> str:
    return " ".join(str(sheet["name"]).split())


def _names(names: list[str]) -> str:
    if len(names) <= MAX_NAMES_PER_ROLE:
        return ", ".join(names)
    shown = ", ".join(names[:MAX_NAMES_PER_ROLE])
    return f"{shown} 외 {len(names) - MAX_NAMES_PER_ROLE}개"


def _limitations(execution: AgentExecution, index_truncated: bool) -> list[str]:
    limitations = []
    if index_truncated:
        limitations.append("대용량 워크북의 일부 관련 셀은 검색 범위에서 제외되었습니다.")
    if any(step.status is AgentStepStatus.FAILED for step in execution.steps):
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    return limitations
