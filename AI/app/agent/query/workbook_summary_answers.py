from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.comparison_evidence import (
    available_evidence,
    matched_comparison_evidence,
    present_comparison_evidence,
)
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus
from app.agent.query.workbook_summary_rows import is_workbook_summary_question

MAX_PRESENTED_EVIDENCE = 120


def validated_workbook_summary_answer(
    question: str,
    execution: AgentExecution,
    index_truncated: bool,
) -> QuestionAnswer | None:
    if not is_workbook_summary_question(question):
        return None
    source = _verified_summary_source(execution)
    if source is None:
        return None
    overview, references = source
    evidence, missing = matched_comparison_evidence(
        references, available_evidence(execution)
    )
    if not evidence or missing:
        return None
    failed = any(step.status is AgentStepStatus.FAILED for step in execution.steps)
    limitations = []
    if index_truncated:
        limitations.append("대용량 워크북의 일부 관련 셀은 검색 범위에서 제외되었습니다.")
    if failed:
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    limited = bool(limitations)
    return QuestionAnswer(
        question=question,
        answer=overview,
        status=QuestionAnswerStatus.LIMITED if limited else QuestionAnswerStatus.ANSWERED,
        confidence=0.7 if limited else 1.0,
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[
            present_comparison_evidence(item)
            for item in evidence[:MAX_PRESENTED_EVIDENCE]
        ],
        limitations=limitations,
    )


def _verified_summary_source(
    execution: AgentExecution,
) -> tuple[str, list[str]] | None:
    for step in execution.steps:
        if (
            step.status is not AgentStepStatus.SUCCEEDED
            or step.tool_name != "search_workbook_data"
            or not step.result
            or step.result.data.get("workbook_summary_query") is not True
        ):
            continue
        overview = str(step.result.data.get("verified_overview") or "").strip()
        references = _support_references(step.result.data.get("verified_insights"))
        if overview and references:
            return overview, references
    return None


def _support_references(insights: object) -> list[str]:
    if not isinstance(insights, list):
        return []
    references = []
    for insight in insights:
        if not isinstance(insight, dict):
            continue
        values = insight.get("support_references")
        if not isinstance(values, list):
            values = insight.get("required_references", [])
        references.extend(value for value in values if isinstance(value, str))
    return list(dict.fromkeys(references))
