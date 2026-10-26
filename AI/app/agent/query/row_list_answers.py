"""조건에 맞는 행 목록을 코드가 직접 문장으로 만든다."""
from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.comparison_evidence import (
    available_evidence,
    matched_comparison_evidence,
    present_comparison_evidence,
)
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus
from app.agent.query.cell_lookup_validation import valid_cell_lookup
from app.services.insights.display.glossary import readable
from app.agent.query.source_count_answers import checked_legacy_count

MAX_NAMED = 12


def validated_row_list_answer(
    question: str,
    execution: AgentExecution,
    index_truncated: bool,
    available: dict[str, object] | None = None,
    *, summary=None, data_index=None,
) -> QuestionAnswer | None:
    found = _row_list(execution)
    if found is not None:
        text, references = _answer(found)
    elif (found := _step_data(execution, "mark_peak", "count")) is not None:
        text, references = _peak_answer(found)
    elif (found := _cell_lookup(execution)) is not None:
        if not valid_cell_lookup(question, found, available or available_evidence(execution)):
            return None
        text, references = _lookup_answer(found)
    else:
        found = _row_count(execution)
        if found is None:
            return None
        return checked_legacy_count(question, found, summary, data_index)
    if not text:
        return None
    available = available if available is not None else available_evidence(execution)
    evidence, missing = matched_comparison_evidence(references, available)
    if not evidence or missing:
        return None
    limitations = []
    if index_truncated:
        limitations.append("대용량 워크북의 일부 관련 셀은 검색 범위에서 제외되었습니다.")
    if any(step.status is AgentStepStatus.FAILED for step in execution.steps):
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    return QuestionAnswer(
        question=question,
        answer=text,
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        confidence=0.7 if limitations else 1.0,
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[present_comparison_evidence(item) for item in evidence],
        limitations=limitations,
    )


def _peak_answer(found: dict) -> tuple[str, list[str]]:
    column = readable(found.get("header") or "항목")
    text = (
        f"{found['mark']}이(가) 가장 많은 항목은 ‘{column}’으로 "
        f"{found['count']}건입니다."
    )
    references = [
        found.get("header_reference"),
        found.get("first_reference"),
        found.get("last_reference"),
    ]
    return text, [value for value in references if isinstance(value, str)]


def _cell_lookup(execution: AgentExecution) -> dict | None:
    return _step_data(execution, "cell_lookup", "value_reference")


def _lookup_answer(found: dict) -> tuple[str, list[str]]:
    subject = found.get("label") or readable(found.get("label_header") or "항목")
    column = readable(found.get("header") or "값")
    text = f"{subject}의 {column} 값은 {found['value']}입니다."
    references = [
        found.get("header_reference"),
        found.get("label_reference"),
        found.get("value_reference"),
    ]
    return text, [value for value in references if isinstance(value, str)]


def _step_data(execution: AgentExecution, key: str, required: str) -> dict | None:
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        found = step.result.data.get(key)
        if isinstance(found, dict) and found.get(required):
            return found
    return None


def _row_count(execution: AgentExecution) -> dict | None:
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        found = step.result.data.get("row_count")
        if isinstance(found, dict) and found.get("count"):
            return found
    return None


def _row_list(execution: AgentExecution) -> dict | None:
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        found = step.result.data.get("row_list")
        if isinstance(found, dict) and found.get("matches"):
            return found
    return None


def _answer(found: dict) -> tuple[str, list[str]]:
    matches = found["matches"]
    names = [str(item["label"]).strip() for item in matches]
    marks = sorted({str(item["value"]).strip()[:1] for item in matches})
    listed = ", ".join(names[:MAX_NAMED])
    listed += " 등" if len(names) > MAX_NAMED else ""
    subject = readable(found.get("label_header") or "항목")
    column = readable(found.get("header") or "")
    text = (
        f"‘{column}’이(가) {'/'.join(marks)}인 {subject}는 "
        f"{listed} {len(names)}건입니다."
    )
    trailing = []
    if found.get("other_count"):
        trailing.append(f"다른 표시가 {found['other_count']}건")
    if found.get("blank_count"):
        trailing.append(f"표시되지 않은 {subject}가 {found['blank_count']}건")
    if trailing:
        text += " " + ", ".join(trailing) + " 있습니다."
    references = [found.get("header_reference"), found.get("label_reference")]
    for item in matches:
        references.extend([item.get("label_reference"), item.get("value_reference")])
    return text, [value for value in references if isinstance(value, str)]
