import asyncio
from app.agent.contracts import AgentToolContext
from app.agent.execution import AgentToolExecutor
from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.conversation_answers import answer_in_conversation
from app.agent.query.question_intent_resolution import resolve_question_intent
from app.agent.query.conversation_models import QuestionConversation, QuestionContextResolver
from app.agent.query.header_relation_answers import header_relation_answer
from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.metric_scalar_answers import metric_scalar_answer
from app.agent.query.metric_semantic_guard import incompatible_metric_answer
from app.agent.query.index import WorkbookDataIndex
from app.agent.query.identifier_answers import missing_identifier_answer
from app.agent.query.intent_models import QuestionIntent, QuestionIntentClassifier
from app.agent.query.interpretation_answers import asks_interpretation, finish_interpretation_answer
from app.agent.query.models import QuestionAnswer, QuestionAnswerGenerator
from app.agent.query.question_validation import vague_question_answer
from app.agent.query.question_formula_answers import direct_formula_answer, missing_formula_answer
from app.agent.query.question_formula_evidence import finish_formula_answer
from app.agent.query.question_formula_sources import prepare_formula_sources
from app.agent.query.question_search_scope import search_scope_truncated as _search_scope_truncated
from app.agent.query.relational_execution import relational_query_answer
from app.agent.query.relational_routing import missing_relational_plan_answer
from app.agent.query.router import build_question_plan
from app.agent.query.source_lookup_answers import source_lookup_answer
from app.agent.query.source_count_answers import source_count_answer
from app.agent.query.source_aggregate_answers import source_aggregate_answer
from app.agent.query.tabular_routing import planned_tabular_answer
from app.agent.query.tabular_source_alias_resolution import clarified_answer
from app.agent.query.time_series_answers import time_series_answer
from app.agent.query.query_replanning import (
    answer_with_replanning, missing_plan_answer, missing_plan_repairable, unavailable_plan,
)
from app.agent.query.question_canonical_answers import canonical_answer
from app.agent.query.question_generation import generate_answer
from app.agent.query.structured_question_answers import structured_question_answer
from app.agent.query.composite_execution import composite_answer
from app.agent.registry import AgentToolRegistry
from app.services.workbook_parsing.models import WorkbookSummary
from app.agent.query.question_capabilities import unavailable_workbook_answer, with_workbook_limitations
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
        if unavailable := unavailable_workbook_answer(question, summary):
            return unavailable
        sources = await asyncio.to_thread(prepare_formula_sources, summary, data_index)
        answer = await answer_in_conversation(
            question, context, sources, self._context_resolver, self._answer_prepared
        )
        answer = (answer if "composite_question" in answer.selected_tools else
                  finish_interpretation_answer(finish_formula_answer(answer, sources)))
        return with_workbook_limitations(answer, summary)
    async def _answer_prepared(self, question, sources, *, intent_override=None,
                               allow_replan=True, allow_composite=True) -> QuestionAnswer:
        return await answer_with_replanning(self, question, sources, intent_override=intent_override,
            allow_replan=allow_replan, allow_composite=allow_composite)
    async def _answer_once(self, question, sources, *, intent_override=None,
                           allow_composite=True, allow_generation=True, intents=None,
                           pending_generation=None) -> QuestionAnswer:
        summary, data_index = sources.summary, sources.index
        # An address lookup must not be redirected by words in a sheet name.
        if direct := await asyncio.to_thread(source_lookup_answer, question, sources):
            return direct
        structured = await structured_question_answer(self, question, sources,
            intent_override=intent_override, allow_composite=allow_composite, intents=intents)
        if structured is not None:
            return structured
        if incompatible := incompatible_metric_answer(question, summary, data_index):
            return incompatible
        if trend := await asyncio.to_thread(time_series_answer, question, summary, data_index):
            return trend
        if counted := await asyncio.to_thread(source_count_answer, question, summary, data_index):
            return counted
        if clarification := vague_question_answer(question, data_index):
            return clarification
        if missing := missing_identifier_answer(question, data_index):
            return missing
        intent = intent_override or await self._question_intent(question, summary)
        if intents is not None:
            intents.append(intent)
        if intent.composite_query is not None:
            return (await composite_answer(question, sources, intent, self._answer_prepared)
                    if allow_composite else unavailable_plan(question))
        # Explicit plans face their own checks; the fallback cannot bypass them.
        if intent.tabular_query is None and intent.relational_query is None:
            if aggregated := await asyncio.to_thread(source_aggregate_answer, question, summary, data_index):
                return aggregated
        if relation := header_relation_answer(question, summary, data_index, intent):
            return relation
        if clarification := missing_relational_plan_answer(question, summary, intent):
            return clarification
        if clarification := ambiguous_source_answer(question, summary, data_index, intent):
            return (await clarified_answer(question, summary, data_index, intent, clarification)
                    if allow_generation else clarification)
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
            return (await clarified_answer(question, summary, data_index, intent, tabular)
                    if allow_generation else tabular)
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
        if canonical := canonical_answer(question, execution, truncated, summary, data_index, intent):
            return canonical
        if not allow_generation:
            return unavailable_plan(question)
        if (pending_generation is not None
                and missing_plan_repairable(question, intent, summary)):
            pending_generation.append((execution, truncated))
            return missing_plan_answer(question)
        return await generate_answer(self._generator, question, summary, execution, truncated, data_index)
    async def _question_intent(self, question: str, summary: WorkbookSummary) -> QuestionIntent:
        return await resolve_question_intent(self._classifier, question, summary)
