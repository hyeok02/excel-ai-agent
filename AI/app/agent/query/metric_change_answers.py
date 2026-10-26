"""이름을 댄 항목 하나의 변화를 코드가 직접 문장으로 만든다."""
from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.comparison_evidence import (
    available_evidence,
    comparison_change_matches,
    comparison_period,
    comparison_values_match,
    matched_comparison_evidence,
    present_comparison_evidence,
)
from app.agent.query.comparison_value_format import (
    comparison_values,
    people_unit,
    percentage_formats,
)
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.services.insights.display.glossary import readable
from app.services.insights.narratives.narrative_values import topic_particle

MAX_NAMED = 8


def validated_metric_change_answer(
    question: str,
    execution: AgentExecution,
    index_truncated: bool,
    available: dict[str, object] | None = None,
) -> QuestionAnswer | None:
    if counted := _counted_answer(question, execution, index_truncated, available):
        return counted
    found = _metric_change(execution)
    if found is None:
        return None
    if not comparison_change_matches(
        found["start_value"], found["end_value"], found["change"]
    ):
        return None
    references = [
        *found["header_references"],
        *found.get("period_references", []),
        found["start_reference"],
        found["end_reference"],
    ]
    checks = (
        (found["start_reference"], found["start_value"]),
        (found["end_reference"], found["end_value"]),
    )
    return _answered(
        question, execution, index_truncated, available,
        _text(question, found), references, checks,
    )


def _answered(question, execution, index_truncated, available, text, references, checks):
    available = available if available is not None else available_evidence(execution)
    evidence, missing = matched_comparison_evidence(references, available)
    if not evidence or missing or not comparison_values_match(checks, available):
        return None
    limitations = []
    if index_truncated:
        limitations.append("대용량 워크북의 일부 관련 셀은 검색 범위에서 제외되었습니다.")
    failed = any(step.status is AgentStepStatus.FAILED for step in execution.steps)
    if failed:
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    return QuestionAnswer(
        question=question,
        answer=text,
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        confidence=0.7 if failed else (0.93 if limitations else 1.0),
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[present_comparison_evidence(item) for item in evidence],
        limitations=limitations,
        verification=QuestionAnswerVerification(
            level="source_checked", checks=["cited_cells", *(["source_values"] if checks else [])]
        ),
    )


def _step_data(
    execution: AgentExecution, key: str, required: str
) -> dict | None:
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        data = step.result.data
        if data.get("answer_scope") == "whole_workbook":
            continue
        found = data.get(key)
        if isinstance(found, dict) and found.get(required):
            return found
    return None


def _text(question: str, found: dict) -> str:
    change = float(found["change"])
    start_format = found.get("start_number_format")
    end_format = found.get("end_number_format")
    start, end, moved = comparison_values(
        found["start_value"], found["end_value"], change,
        start_format, end_format, people_unit(question, found["header"]),
    )
    period = (
        f"{comparison_period(found.get('start_date'))}부터 "
        f"{comparison_period(found.get('end_date'))}까지 "
        if found.get("start_date") and found.get("end_date")
        else ""
    )
    subject = readable(found["header"])
    if change == 0:
        return f"{period}{subject}{topic_particle(subject)} {start}에서 {end}으로 변동이 없었습니다."
    verb = "감소" if change < 0 else "증가"
    share = "" if percentage_formats(start_format, end_format) else _share(
        found["start_value"], change
    )
    return (
        f"{period}{subject}{topic_particle(subject)} "
        f"{start}에서 {end}으로 {moved}{share} {verb}했습니다."
    )


def _share(start: object, change: float) -> str:
    """증감률. 시작이 0이면 비율이 뜻을 잃으므로 적지 않는다."""
    try:
        base = abs(float(start))
    except (TypeError, ValueError):
        return ""
    return f"({abs(change) / base * 100:.1f}%)" if base else ""


def _counted_answer(question, execution, index_truncated, available):
    """'부서가 총 몇 개야?' 처럼 지표 수를 묻는 질문."""
    found = _step_data(
        execution, "metric_count", "count"
    )
    if found is None:
        return None
    listed = ", ".join(str(name) for name in found["names"][:MAX_NAMED])
    if len(found["names"]) > MAX_NAMED:
        listed += " 등"
    text = f"{found['group']}는 {listed} 모두 {found['count']}개입니다."
    return _answered(
        question, execution, index_truncated, available, text, found["references"], ()
    )


def _metric_change(execution: AgentExecution) -> dict | None:
    return _step_data(
        execution, "named_metric_change", "header",
    )
