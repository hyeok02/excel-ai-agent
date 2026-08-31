import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from app.agent.contracts import AgentToolContext, InvalidToolArgumentsError
from app.agent.execution.models import (
    AgentExecution,
    AgentExecutionStatus,
    AgentStepError,
    AgentStepExecution,
    AgentStepStatus,
    AgentToolExecutionResult,
)
from app.agent.planning.models import AgentExecutionPlan, AgentPlanStep, StepFailurePolicy
from app.agent.registry import AgentToolRegistry, ToolNotFoundError

logger = logging.getLogger(__name__)


class AgentToolExecutor:
    def __init__(self, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(UTC))

    def execute(
        self,
        plan: AgentExecutionPlan,
        context: AgentToolContext,
        registry: AgentToolRegistry,
    ) -> AgentExecution:
        started_at = self._clock()
        steps: list[AgentStepExecution] = []
        statuses: dict[str, AgentStepStatus] = {}
        halted = False
        for step in plan.steps:
            if halted:
                outcome = self._skipped(step, "EXECUTION_HALTED", "앞 단계 실패로 실행이 중단됐습니다.")
            elif any(statuses.get(item) is not AgentStepStatus.SUCCEEDED for item in step.depends_on):
                outcome = self._skipped(
                    step, "DEPENDENCY_NOT_SUCCEEDED", "선행 단계가 성공하지 않아 실행하지 않았습니다."
                )
            else:
                outcome = self._execute_step(step, context, registry)
            steps.append(outcome)
            statuses[step.id] = outcome.status
            if outcome.status is AgentStepStatus.FAILED and step.on_failure is StepFailurePolicy.STOP:
                halted = True
        return self._complete(plan, started_at, steps)

    def _execute_step(self, step, context, registry) -> AgentStepExecution:
        started_at = self._clock()
        try:
            result = registry.execute(step.tool_name, context, step.arguments)
            payload = AgentToolExecutionResult(
                summary=result.summary,
                data=dict(result.data),
                evidence=list(result.evidence),
            )
            return self._step(step, AgentStepStatus.SUCCEEDED, started_at, result=payload)
        except ToolNotFoundError as exception:
            error = AgentStepError(code="TOOL_NOT_FOUND", message=str(exception))
        except InvalidToolArgumentsError as exception:
            error = AgentStepError(code="INVALID_ARGUMENTS", message=str(exception))
        except Exception:
            logger.exception("Agent Tool 실행 실패: %s", step.tool_name)
            error = AgentStepError(
                code="TOOL_EXECUTION_FAILED",
                message="도구 실행 중 예상하지 못한 오류가 발생했습니다.",
                retryable=True,
            )
        return self._step(step, AgentStepStatus.FAILED, started_at, error=error)

    def _step(self, step, status, started_at, result=None, error=None):
        return AgentStepExecution(
            step_id=step.id,
            title=step.title,
            tool_name=step.tool_name,
            purpose=step.purpose,
            expected_output=step.expected_output,
            status=status,
            started_at=started_at,
            completed_at=self._clock(),
            result=result,
            error=error,
        )

    def _skipped(self, step: AgentPlanStep, code: str, message: str) -> AgentStepExecution:
        return self._step(
            step, AgentStepStatus.SKIPPED, None, error=AgentStepError(code=code, message=message)
        )

    def _complete(self, plan, started_at, steps) -> AgentExecution:
        succeeded = sum(item.status is AgentStepStatus.SUCCEEDED for item in steps)
        failed = sum(item.status is AgentStepStatus.FAILED for item in steps)
        skipped = sum(item.status is AgentStepStatus.SKIPPED for item in steps)
        status = AgentExecutionStatus.SUCCEEDED
        if failed:
            status = AgentExecutionStatus.PARTIAL if succeeded else AgentExecutionStatus.FAILED
        summary = f"계획 {len(steps)}단계 중 {succeeded}단계 성공, {failed}단계 실패, {skipped}단계 건너뜀"
        return AgentExecution(
            execution_id=str(uuid4()),
            status=status,
            summary=summary,
            started_at=started_at,
            completed_at=self._clock(),
            succeeded_step_count=succeeded,
            failed_step_count=failed,
            skipped_step_count=skipped,
            plan=plan,
            steps=steps,
        )
