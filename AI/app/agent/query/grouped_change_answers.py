"""Answer item-by-item endpoint comparisons directly from verified cells."""

from app.agent.execution import AgentExecution, AgentStepStatus
from app.agent.query.comparison_evidence import available_evidence, comparison_period
from app.agent.query.grouped_change_evidence import grouped_change_proof
from app.agent.query.grouped_change_selection import selected_grouped_changes
from app.agent.query.metric_change_answers import _answered, _text
from app.agent.query.models import QuestionAnswer

GROUP_NAMES = {"department": "부서별", "role": "직무별"}


def validated_grouped_change_answer(
    question: str, execution: AgentExecution, index_truncated: bool,
) -> QuestionAnswer | None:
    candidates = {}
    for step in execution.steps:
        if step.status is not AgentStepStatus.SUCCEEDED or not step.result:
            continue
        if step.result.data.get("answer_scope") == "whole_workbook":
            continue
        comparison = step.result.data.get("time_series_comparison")
        metrics = selected_grouped_changes(question, comparison)
        if metrics:
            key = tuple((item["start_reference"], item["end_reference"]) for item in metrics)
            candidates[key] = comparison, metrics
    if len(candidates) != 1:
        return None
    comparison, metrics = next(iter(candidates.values()))
    available = available_evidence(execution)
    proof = grouped_change_proof(question, comparison, metrics, available)
    if proof is None:
        return None
    period = (
        f"{comparison_period(comparison['start_date'])}부터 "
        f"{comparison_period(comparison['end_date'])}까지"
    )
    group = GROUP_NAMES.get(comparison.get("metric_group"), "항목별")
    lines = [f"{period} {group} 시작 값과 마지막 값을 비교했습니다.", ""]
    for metric in metrics:
        # The shared period has already been verified and is shown once above.
        item = {**metric, "start_date": None, "end_date": None}
        lines.append(f"- {_text(question, item)}")
    return _answered(
        question, execution, index_truncated, available, "\n".join(lines), *proof,
    )
