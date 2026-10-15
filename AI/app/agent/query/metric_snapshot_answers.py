"""Render latest time-series values directly from source cells."""

from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.comparison_evidence import (
    available_evidence,
    comparison_period,
    matched_comparison_evidence,
    present_comparison_evidence,
)
from app.agent.query.comparison_value_format import comparison_values, people_unit
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus
from app.services.insights.display.glossary import readable
from app.services.insights.narratives.narrative_values import topic_particle

MAX_ITEMS = 12


def validated_metric_snapshot_answer(
    question: str,
    execution: AgentExecution,
    index_truncated: bool,
) -> QuestionAnswer | None:
    found = _snapshot(execution)
    if found is None:
        return None
    metrics = found.get("metrics")
    if not isinstance(metrics, list) or not metrics:
        return None
    shown = [item for item in metrics[:MAX_ITEMS] if _valid_item(item)]
    if not shown:
        return None
    references = _references(found, shown)
    evidence, missing = matched_comparison_evidence(
        references, available_evidence(execution)
    )
    if not evidence or missing:
        return None
    limitations = []
    if len(metrics) > len(shown):
        limitations.append(f"항목이 많아 앞의 {MAX_ITEMS}개만 표시했습니다.")
    if index_truncated:
        limitations.append("대용량 워크북의 일부 관련 셀은 검색 범위에서 제외되었습니다.")
    if any(step.status is AgentStepStatus.FAILED for step in execution.steps):
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    return QuestionAnswer(
        question=question,
        answer=_text(question, found, shown),
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        confidence=0.7 if limitations else 1.0,
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[present_comparison_evidence(item) for item in evidence],
        limitations=limitations,
    )


def _snapshot(execution: AgentExecution) -> dict | None:
    for step in execution.steps:
        if step.status is AgentStepStatus.SUCCEEDED and step.result:
            found = step.result.data.get("metric_snapshot")
            if isinstance(found, dict):
                return found
    return None


def _valid_item(item: object) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("header"), str)
        and item.get("value") is not None
        and isinstance(item.get("value_reference"), str)
    )


def _references(found: dict, metrics: list[dict]) -> list[str]:
    values = [found.get("period_reference")]
    for item in metrics:
        values.extend(item.get("header_references") or ())
        values.append(item["value_reference"])
    return list(dict.fromkeys(value for value in values if isinstance(value, str)))


def _text(question: str, found: dict, metrics: list[dict]) -> str:
    unit = people_unit(question, " ".join(str(item["header"]) for item in metrics))
    values = ", ".join(
        f"{readable(item['header'])} {_display_value(item, unit)}"
        for item in metrics
    )
    period = comparison_period(found.get("end_date"))
    group = found.get("group")
    subject = f"{group}별 {'직원 수' if unit else '값'}" if group else "확인된 값"
    return f"{period} 기준 {subject}{topic_particle(subject)} {values}입니다."


def _display_value(item: dict, unit: str) -> str:
    number_format = item.get("number_format")
    return comparison_values(
        item["value"], item["value"], 0,
        number_format, number_format, unit,
    )[0]
