"""Answer observed-period questions from the two cited date cells."""

from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.comparison_evidence import (
    available_evidence,
    comparison_period,
    matched_comparison_evidence,
    present_comparison_evidence,
)
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus

GROUP_NAMES = {"department": "부서별", "role": "직무별"}


def validated_metric_period_answer(
    question: str, execution: AgentExecution, index_truncated: bool
) -> QuestionAnswer | None:
    found = _period(execution)
    if found is None:
        return None
    references = [found["start_reference"], found["end_reference"]]
    evidence, missing = matched_comparison_evidence(
        references, available_evidence(execution)
    )
    if not evidence or missing:
        return None
    limitations = []
    if index_truncated:
        limitations.append("대용량 워크북의 일부 관련 셀은 검색 범위에서 제외되었습니다.")
    if any(step.status is AgentStepStatus.FAILED for step in execution.steps):
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    group = GROUP_NAMES.get(str(found.get("metric_group")), "시계열")
    answer = (
        f"확인된 {group} 데이터 기간은 {comparison_period(found['start_date'])}부터 "
        f"{comparison_period(found['end_date'])}까지입니다."
    )
    return QuestionAnswer(
        question=question,
        answer=answer,
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        confidence=0.7 if limitations else 1.0,
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[present_comparison_evidence(item) for item in evidence],
        limitations=limitations,
    )


def _period(execution: AgentExecution) -> dict | None:
    for step in execution.steps:
        if step.status is AgentStepStatus.SUCCEEDED and step.result:
            found = step.result.data.get("metric_period")
            if isinstance(found, dict) and all(
                found.get(key) for key in ("start_date", "end_date", "start_reference", "end_reference")
            ):
                return found
    return None
