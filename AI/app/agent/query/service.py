from app.agent.contracts import AgentToolContext
from app.agent.execution import AgentToolExecutor
from app.agent.query.answer_validation import validate_answer
from app.agent.query.context import execution_context
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.models import (
    QuestionAnswer,
    QuestionAnswerGenerator,
)
from app.agent.query.question_validation import unclear_draft_answer, vague_question_answer
from app.agent.query.router import build_question_plan
from app.agent.registry import AgentToolRegistry
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
        return validate_answer(question, draft, execution, data_index.truncated)
