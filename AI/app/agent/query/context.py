from app.agent.execution import AgentExecution

MAX_MODEL_EVIDENCE_PER_STEP = 120


def execution_context(execution: AgentExecution) -> dict[str, object]:
    return {
        "status": execution.status,
        "summary": execution.summary,
        "steps": [_step_context(step) for step in execution.steps],
    }


def _step_context(step) -> dict[str, object]:
    result = step.result
    evidence = result.evidence if result else []
    return {
        "tool_name": step.tool_name,
        "status": step.status,
        "summary": result.summary if result else None,
        "data": _model_step_data(step.tool_name, result.data) if result else None,
        "evidence": [
            item.model_dump(mode="json")
            for item in evidence[:MAX_MODEL_EVIDENCE_PER_STEP]
        ],
        "evidence_count": len(evidence),
        "evidence_truncated": len(evidence) > MAX_MODEL_EVIDENCE_PER_STEP,
    }


def _model_step_data(tool_name: str, data: object) -> object:
    if tool_name != "search_workbook_data" or not isinstance(data, dict):
        return data
    # 셀 상세는 evidence에도 같은 값과 주소로 들어가므로 한 번만 모델에 전달한다.
    return {key: value for key, value in data.items() if key != "rows"}
