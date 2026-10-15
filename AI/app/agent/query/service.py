import asyncio

from app.agent.contracts import AgentToolContext
from app.agent.execution import AgentToolExecutor
from app.agent.query.answer_validation import validate_answer
from app.agent.query.comparison_answers import validated_comparison_answer
from app.agent.query.grouped_change_answers import validated_grouped_change_answer
from app.agent.query.metric_change_answers import validated_metric_change_answer
from app.agent.query.metric_period_answers import validated_metric_period_answer
from app.agent.query.metric_snapshot_answers import validated_metric_snapshot_answer
from app.agent.query.row_list_answers import validated_row_list_answer
from app.agent.query.context import execution_context
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.identifier_answers import missing_identifier_answer
from app.agent.query.intent_models import QuestionIntent, QuestionIntentClassifier
from app.agent.query.models import (
    QuestionAnswer,
    QuestionAnswerGenerator,
)
from app.agent.query.question_validation import unclear_draft_answer, vague_question_answer
from app.agent.query.router import build_question_plan
from app.agent.query.structure_answers import validated_structure_answer
from app.agent.query.tabular_routing import planned_tabular_answer
from app.agent.query.workbook_summary_answers import validated_workbook_summary_answer
from app.agent.query.verified_insight_answers import validated_verified_insight_answer
from app.agent.registry import AgentToolRegistry
from app.services.workbook_parsing.models import WorkbookSummary


class WorkbookQuestionService:
    def __init__(
        self,
        generator: QuestionAnswerGenerator,
        registry: AgentToolRegistry,
        executor: AgentToolExecutor | None = None,
        classifier: QuestionIntentClassifier | None = None,
    ) -> None:
        self._generator = generator
        self._registry = registry
        self._executor = executor or AgentToolExecutor()
        self._classifier = classifier

    async def answer(
        self, question: str, summary: WorkbookSummary, data_index: WorkbookDataIndex
    ) -> QuestionAnswer:
        if clarification := vague_question_answer(question, data_index):
            return clarification
        if missing := missing_identifier_answer(question, data_index):
            return missing
        intent = await self._question_intent(question, summary)
        if tabular := planned_tabular_answer(intent, summary, data_index, question):
            return tabular
        plan = build_question_plan(question)
        execution = await asyncio.to_thread(
            self._executor.execute,
            plan,
            AgentToolContext(summary, data_index, question, intent),
            self._registry,
        )
        truncated = _search_scope_truncated(execution)
        if canonical := validated_comparison_answer(question, execution, truncated):
            return canonical
        if canonical := validated_grouped_change_answer(question, execution, truncated):
            return canonical
        if canonical := validated_metric_period_answer(question, execution, truncated):
            return canonical
        if canonical := validated_metric_snapshot_answer(question, execution, truncated):
            return canonical
        if canonical := validated_metric_change_answer(question, execution, truncated):
            return canonical
        if canonical := validated_row_list_answer(question, execution, truncated):
            return canonical
        if canonical := validated_structure_answer(question, execution, truncated):
            return canonical
        if canonical := validated_workbook_summary_answer(question, execution, truncated):
            return canonical
        if canonical := validated_verified_insight_answer(
            question, execution, truncated, intent
        ):
            return canonical
        draft = await self._generator.generate(
            question, summary.filename, execution_context(execution)
        )
        if clarification := unclear_draft_answer(question, draft):
            return clarification
        return validate_answer(question, draft, execution, truncated)


    async def _question_intent(
        self, question: str, summary: WorkbookSummary
    ) -> QuestionIntent:
        """의도 판별이 실패해도 질문에는 답한다. 분류는 힌트일 뿐이다."""
        if self._classifier is None:
            return QuestionIntent.from_keywords(question)
        try:
            return await self._classifier.classify(question, summary)
        except Exception:
            return QuestionIntent.from_keywords(question)


def _search_scope_truncated(execution) -> bool:
    return any(
        bool(step.result.data.get("index_truncated"))
        for step in execution.steps
        if step.result and isinstance(step.result.data, dict)
    )
