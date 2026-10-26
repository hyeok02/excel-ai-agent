import asyncio
from app.agent.contracts import AgentToolContext
from app.agent.execution import AgentToolExecutor
from app.agent.query.answer_validation import validate_answer
from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.comparison_answers import validated_comparison_answer
from app.agent.query.conversation_answers import answer_in_conversation
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.conversation_models import QuestionConversation, QuestionContextResolver
from app.agent.query.grouped_change_answers import validated_grouped_change_answer
from app.agent.query.header_relation_answers import header_relation_answer
from app.agent.query.metric_change_answers import validated_metric_change_answer
from app.agent.query.metric_period_answers import validated_metric_period_answer
from app.agent.query.metric_snapshot_answers import validated_metric_snapshot_answer
from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.metric_scalar_answers import metric_scalar_answer
from app.agent.query.metric_semantic_guard import incompatible_metric_answer
from app.agent.query.row_list_answers import validated_row_list_answer
from app.agent.query.context import execution_context
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.identifier_answers import missing_identifier_answer
from app.agent.query.intent_models import QuestionIntent, QuestionIntentClassifier
from app.agent.query.interpretation_answers import asks_interpretation, finish_interpretation_answer
from app.agent.query.models import QuestionAnswer, QuestionAnswerGenerator
from app.agent.query.question_validation import unclear_draft_answer, vague_question_answer
from app.agent.query.question_formula_answers import direct_formula_answer, missing_formula_answer
from app.agent.query.question_formula_evidence import finish_formula_answer
from app.agent.query.question_formula_sources import prepare_formula_sources
from app.agent.query.question_search_scope import search_scope_truncated as _search_scope_truncated
from app.agent.query.relational_execution import relational_query_answer
from app.agent.query.relational_routing import missing_relational_plan_answer
from app.agent.query.router import build_question_plan
from app.agent.query.structure_answers import validated_structure_answer
from app.agent.query.source_lookup_answers import source_lookup_answer
from app.agent.query.tabular_routing import planned_tabular_answer
from app.agent.query.tabular_source_alias_resolution import clarified_answer
from app.agent.query.time_series_answers import time_series_answer
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
        context_resolver: QuestionContextResolver | None = None,
    ) -> None:
        self._generator = generator
        self._registry = registry
        self._executor = executor or AgentToolExecutor()
        self._classifier = classifier
        self._context_resolver = context_resolver

    async def answer(
        self, question: str, summary: WorkbookSummary, data_index: WorkbookDataIndex,
        context: QuestionConversation | None = None,
    ) -> QuestionAnswer:
        sources = await asyncio.to_thread(prepare_formula_sources, summary, data_index)
        answer = await answer_in_conversation(
            question, context, sources, self._context_resolver, self._answer_prepared
        )
        return finish_interpretation_answer(finish_formula_answer(answer, sources))

    async def _answer_prepared(self, question, sources) -> QuestionAnswer:
        summary, data_index = sources.summary, sources.index
        if incompatible := incompatible_metric_answer(question, summary, data_index):
            return incompatible
        if trend := await asyncio.to_thread(time_series_answer, question, summary, data_index):
            return trend
        if direct := await asyncio.to_thread(source_lookup_answer, question, sources):
            return direct
        if clarification := vague_question_answer(question, data_index):
            return clarification
        if missing := missing_identifier_answer(question, data_index):
            return missing
        intent = await self._question_intent(question, summary)
        if relation := header_relation_answer(question, summary, data_index, intent):
            return relation
        if clarification := missing_relational_plan_answer(question, summary, intent):
            return clarification
        if clarification := ambiguous_source_answer(question, summary, data_index, intent):
            return await clarified_answer(question, summary, data_index, intent, clarification)
        if formula := direct_formula_answer(question, sources, intent):
            return formula
        if relational := relational_query_answer(intent.relational_query, summary, data_index, question, intent):
            return relational
        if observed := metric_observation_answer(question, summary, data_index, intent):
            return observed
        scalar = metric_scalar_answer(question, summary, data_index, intent)
        if scalar and scalar.status == "answered" and scalar.verification.level == "request_checked":
            return scalar
        tabular = await asyncio.to_thread(planned_tabular_answer, intent, summary, data_index, question)
        if tabular is not None and "clarify_source_scope" in tabular.selected_tools:
            return await clarified_answer(question, summary, data_index, intent, tabular)
        if tabular is not None and tabular.status != "insufficient_evidence":
            return tabular
        if scalar:
            return scalar
        if missing := missing_formula_answer(question, sources, intent):
            return missing
        if tabular is not None and not asks_interpretation(question):
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
        except Exception as exception:
            raise_for_quota_exhaustion(exception)
            return QuestionIntent.from_keywords(question)
