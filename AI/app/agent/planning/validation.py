from collections.abc import Mapping

from app.agent.contracts import AgentToolMetadata
from app.agent.planning.models import AgentExecutionPlan, PlanGenerationError


def ensure_executable_plan(
    plan: AgentExecutionPlan,
    tools: tuple[AgentToolMetadata, ...],
) -> AgentExecutionPlan:
    available = {tool.name: tool for tool in tools}
    for step in plan.steps:
        metadata = available.get(step.tool_name)
        if metadata is None:
            raise PlanGenerationError(
                f"등록되지 않은 도구가 계획에 포함되었습니다: {step.tool_name}"
            )
        _validate_arguments(step.id, step.arguments, metadata.input_schema)
    return plan


def _validate_arguments(
    step_id: str,
    arguments: Mapping[str, object],
    schema: Mapping[str, object],
) -> None:
    unknown = sorted(set(arguments) - set(schema))
    if unknown:
        raise PlanGenerationError(
            f"{step_id}에 지원하지 않는 인자가 있습니다: {', '.join(unknown)}"
        )
    for name, raw_rule in schema.items():
        rule = raw_rule if isinstance(raw_rule, Mapping) else {}
        if rule.get("required") is True and name not in arguments:
            raise PlanGenerationError(f"{step_id}에 필수 인자 {name}이 없습니다.")
        if name in arguments:
            _validate_value(step_id, name, arguments[name], rule)


def _validate_value(
    step_id: str, name: str, value: object, rule: Mapping[str, object]
) -> None:
    expected = rule.get("type")
    valid_type = (
        expected == "string" and isinstance(value, str) and bool(value.strip())
    ) or (
        expected == "integer" and isinstance(value, int) and not isinstance(value, bool)
    )
    if expected in {"string", "integer"} and not valid_type:
        raise PlanGenerationError(f"{step_id}의 {name} 형식이 올바르지 않습니다.")
    if "enum" in rule and value not in rule["enum"]:
        raise PlanGenerationError(f"{step_id}의 {name} 값이 허용 범위를 벗어났습니다.")
    if isinstance(value, int) and not isinstance(value, bool):
        if "minimum" in rule and value < rule["minimum"]:
            raise PlanGenerationError(f"{step_id}의 {name} 값이 너무 작습니다.")
        if "maximum" in rule and value > rule["maximum"]:
            raise PlanGenerationError(f"{step_id}의 {name} 값이 너무 큽니다.")
