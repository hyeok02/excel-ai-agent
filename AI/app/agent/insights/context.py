import json

from app.agent.execution.models import AgentExecution, AgentStepExecution

MAX_STEP_DATA_CHARS = 12_000
MAX_EVIDENCE_PER_STEP = 40


def build_execution_insight_context(execution: AgentExecution) -> dict[str, object]:
    plan = execution.plan
    return {
        "user_intent": plan.user_intent,
        "objective": plan.objective,
        "user_value": plan.user_value,
        "expected_deliverable": plan.expected_deliverable,
        "execution_status": execution.status,
        "execution_summary": execution.summary,
        "steps": [_step_context(step) for step in execution.steps],
        "plan_limitations": plan.limitations,
    }


def _step_context(step: AgentStepExecution) -> dict[str, object]:
    payload: dict[str, object] = {
        "step_id": step.step_id,
        "title": step.title,
        "purpose": step.purpose,
        "expected_output": step.expected_output,
        "status": step.status,
    }
    if step.error:
        payload["error"] = {
            "code": step.error.code,
            "message": step.error.message,
        }
    if not step.result:
        return payload
    data_json = json.dumps(step.result.data, ensure_ascii=False, default=str)
    payload["tool_summary"] = step.result.summary
    payload["data_excerpt"] = data_json[:MAX_STEP_DATA_CHARS]
    payload["data_truncated"] = len(data_json) > MAX_STEP_DATA_CHARS
    evidence = step.result.evidence[:MAX_EVIDENCE_PER_STEP]
    payload["evidence"] = [item.model_dump(mode="json") for item in evidence]
    payload["omitted_evidence_count"] = max(0, len(step.result.evidence) - len(evidence))
    return payload
