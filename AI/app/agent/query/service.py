from app.agent.contracts import AgentToolContext
from app.agent.execution import AgentExecution, AgentStepStatus, AgentToolExecutor
from app.agent.query.context import execution_context
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.models import (
    QuestionAnswer,
    QuestionAnswerDraft,
    QuestionAnswerEvidence,
    QuestionAnswerGenerator,
    QuestionAnswerStatus,
)
from app.agent.query.numeric_support import supported_answer_numbers
from app.agent.query.question_validation import unclear_draft_answer, vague_question_answer
from app.agent.query.router import build_question_plan
from app.agent.registry import AgentToolRegistry
from app.services.insights.numeric_validation import unmatched_numbers
from app.services.workbook_parsing.models import WorkbookSummary


class WorkbookQuestionService:
    def __init__(
        self,
        generator: QuestionAnswerGenerator,
        registry: AgentToolRegistry,
        executor: AgentToolExecutor | None = None,
    ) -> None:
        self._generator = generator
        self._registry = registry
        self._executor = executor or AgentToolExecutor()

    async def answer(
        self, question: str, summary: WorkbookSummary, data_index: WorkbookDataIndex
    ) -> QuestionAnswer:
        if clarification := vague_question_answer(question, data_index):
            return clarification
        plan = build_question_plan(question)
        execution = self._executor.execute(
            plan, AgentToolContext(summary, data_index), self._registry
        )
        draft = await self._generator.generate(
            question, summary.filename, execution_context(execution)
        )
        if clarification := unclear_draft_answer(question, draft):
            return clarification
        return _validate_answer(question, draft, execution, data_index.truncated)

def _validate_answer(
    question: str,
    draft: QuestionAnswerDraft,
    execution: AgentExecution,
    index_truncated: bool,
) -> QuestionAnswer:
    available = _available_evidence(execution)
    requested = [_normalize_reference(item) for item in draft.evidence]
    matched = [available[item] for item in requested if item in available]
    unknown = [item for item in requested if item not in available]
    limitations = list(draft.limitations)
    if unknown:
        limitations.append("AI가 제시한 일부 셀 주소를 Tool 근거에서 확인하지 못했습니다.")
    if index_truncated:
        limitations.append("대용량 워크북의 일부 셀은 검색 범위에서 제외되었습니다.")
    failed = any(step.status is AgentStepStatus.FAILED for step in execution.steps)
    if failed:
        limitations.append("일부 Agent Tool 실행에 실패했습니다.")
    if not matched:
        return QuestionAnswer(
            question=question,
            answer="현재 확인된 원본 셀 근거만으로는 이 질문에 답할 수 없습니다.",
            status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE,
            confidence=0,
            selected_tools=[step.tool_name for step in execution.steps],
            evidence=[],
            limitations=_unique(limitations or ["질문과 직접 연결되는 셀 근거가 없습니다."]),
        )
    supported = supported_answer_numbers(question, matched, execution)
    unsupported_numbers = unmatched_numbers(draft.answer, supported)
    if unsupported_numbers:
        limitations.append("답변의 일부 수치를 인용한 셀에서 확인하지 못했습니다.")
        return QuestionAnswer(
            question=question,
            answer="답변의 수치를 원본 셀과 대조하지 못해 결과를 표시하지 않았습니다.",
            status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE,
            confidence=0,
            selected_tools=[step.tool_name for step in execution.steps],
            evidence=[_present(item) for item in matched],
            limitations=_unique(limitations),
        )
    verification_limited = bool(unknown or failed)
    limited = bool(verification_limited or index_truncated)
    return QuestionAnswer(
        question=question,
        answer=draft.answer,
        status=QuestionAnswerStatus.LIMITED if limited else QuestionAnswerStatus.ANSWERED,
        confidence=min(draft.confidence, 0.7) if verification_limited else draft.confidence,
        selected_tools=[step.tool_name for step in execution.steps],
        evidence=[_present(item) for item in matched],
        limitations=_unique(limitations),
    )


def _available_evidence(execution: AgentExecution) -> dict[str, object]:
    available = {}
    for step in execution.steps:
        if not step.result:
            continue
        for item in step.result.evidence:
            if item.reference:
                key = _normalize_reference(f"{item.sheet_name}!{item.reference}")
                current = available.get(key)
                if current is None or _evidence_quality(item) > _evidence_quality(current):
                    available[key] = item
    return available


def _evidence_quality(item: object) -> int:
    return 2 * int(getattr(item, "value", None) is not None) + int(bool(getattr(item, "formula", None)))


def _normalize_reference(reference: str) -> str:
    return reference.strip().replace("'", "").casefold()


def _present(item) -> QuestionAnswerEvidence:
    content = item.formula or (str(item.value) if item.value is not None else "")
    label = f"{item.description}: {content}" if content else item.description
    return QuestionAnswerEvidence(**item.model_dump(), label=label[:160])


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))
