"""One bounded plan repair; never repair facts, user scope or failed evidence."""
import asyncio

from app.agent.query.models import QuestionAnswer
from app.agent.query.series_binding import answers_nothing, is_unbound, refused_without_basis
from app.agent.query.time_series_answers import series_attempt
from app.agent.query.final_answers import final_answer
from app.agent.query.intent_models import QuestionIntent
from app.agent.query.interpretation_answers import asks_interpretation
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.question_generation import generate_answer
from app.agent.query.resampled_trend_request import requested_grains
from app.agent.query.source_value_settling import settled_answer
from app.agent.query.tabular_routing import unproven_note, unverified_plan
from app.agent.query.replanning_scope import keeps_named_fields, named_field_hint, single_table_recovery_allowed
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_feature_contract import feature_contract_matches
from app.agent.query.tabular_request_scope import request_matches_plan
from app.agent.query.tabular_crosstab_guard import ANOTHER_MEASURE, detail_tables


def missing_plan_repairable(question, intent, summary):
    """Only defer an exhausted model-backed route, never a source refusal.

    Deterministic answers, scope clarification and source errors must run first.
    A keyword/provider fallback must not silently create an extra model call.
    """
    return bool(intent.from_model and not intent.whole_workbook
        and intent.kind in {"other", "aggregation", "cell_lookup", "row_count", "row_list",
                            "comparison", "summary"}
        and not (intent.tabular_query or intent.relational_query
                 or intent.header_relation or intent.composite_query)
        and not asks_interpretation(question) and build_query_tables(summary)
        and single_table_recovery_allowed(question, summary))


def repair_feedback(question, intent, answer, summary):
    if (answer.status != "insufficient_evidence" or answer.evidence
            or answer.clarification_options or not intent.from_model
            or getattr(intent, "composite_query", None)):
        return None
    plan = intent.tabular_query
    if plan is None:
        if (answer.selected_tools == ["intent_resolution"]
                and missing_plan_repairable(question, intent, summary)):
            return {"code": "missing_query_plan", "kind": intent.kind, "previous_plan": None,
                    **named_field_hint(intent, summary)}
        return None
    if answer.selected_tools != ["tabular_query"]:
        return None
    tables = build_query_tables(summary)
    selected = [table for table in tables if table.id == plan.table_id]
    if ANOTHER_MEASURE in answer.limitations:  # say where the value's rows are recorded
        return {"code": "cross_tab_column_holds_another_measure", "kind": intent.kind,
                "previous_plan": plan.model_dump(mode="json"), "value_recorded_in": detail_tables(summary, plan)}
    if len(selected) != 1:
        code = "unknown_table_id"
    else:
        bound = bind_tabular_plan(plan, selected[0])
        if bound is None:
            code = "unknown_or_ambiguous_column_id"
        elif not feature_contract_matches(bound, selected[0]):
            code = "unsupported_operation_fields"
        elif not request_matches_plan(question, bound, selected[0], tables, intent):
            code = "request_scope_or_operation_mismatch"
        else:
            # The plan already matches the request: its failure is not permission
            # to remove source rows, currencies, formulas or ambiguous entities.
            return None
    return {"code": code, "kind": intent.kind, "previous_plan": plan.model_dump(mode="json")}


async def answer_with_replanning(service, question, sources, **options):
    answer = await _answer_with_replanning(service, question, sources, **options)
    if answers_nothing(answer):  # related figures, or cited cells that answer nothing: the last stages still try
        return await asyncio.to_thread(final_answer, question, sources.summary, sources.index) or answer
    if not refused_without_basis(answer):
        return answer  # otherwise an unbound trend refusal says more than a generic one
    refusal = await asyncio.to_thread(series_attempt, question, sources.summary, sources.index)
    if is_unbound(refusal):
        return settled_answer(question, sources, refusal)
    return await asyncio.to_thread(final_answer, question, sources.summary, sources.index) or answer


async def _answer_with_replanning(service, question, sources, *, intent_override=None,
                                  allow_replan=True, allow_composite=True):
    intents = []
    replan = getattr(service._classifier, "replan", None)
    pending = [] if allow_replan and callable(replan) else None
    first = await service._answer_once(question, sources, intent_override=intent_override,
        allow_composite=allow_composite, intents=intents, pending_generation=pending)
    if pending is not None and intents:
        feedback = repair_feedback(question, intents[-1], first, sources.summary)
        if feedback is not None:
            recovered = await _recover(service, question, sources, replan, feedback, intents[-1])
            if recovered is not None:
                return recovered
    if pending:
        # Resume the exact original generation context; do not reclassify,
        # repeat source scans or leak rejected retry targets into the fallback.
        execution, truncated = pending[0]
        generated = await generate_answer(service._generator, question, sources.summary, execution, truncated,
                                          sources.index)
        return unproven_note(generated) if unverified_plan(first) else generated
    return settled_answer(question, sources, first)


async def _recover(service, question, sources, replan, feedback, first=None):
    if not single_table_recovery_allowed(question, sources.summary):
        return None
    try:
        revised = await replan(question, sources.summary, feedback)
        if (not isinstance(revised, QuestionIntent) or revised.whole_workbook
                or revised.composite_query or revised.relational_query or revised.header_relation
                or revised.tabular_query is None
                or first is not None and not keeps_named_fields(first, revised, sources.summary)):
            return None
        retried = await service._answer_once(question, sources, intent_override=revised,
            allow_composite=False, allow_generation=False)
    except Exception as error:
        raise_for_quota_exhaustion(error)
        return None
    # A retry cannot turn mere citations or generated text into request proof. A ranking recomputed
    # over every source row, with its full order and field reading stated, is the limited answer it is.
    checks, grains = set(retried.verification.checks), requested_grains(question)
    ranked = retried.status == "limited" and (
        retried.selected_tools == ["ranked_group_query"] and "ranking" in checks
        # calendar-period totals, in the grain the question names when it names one
        or retried.selected_tools == ["period_group_query"] and "calendar_period" in checks
        and (not grains or len(grains) == 1 and f"calendar_grain_{next(iter(grains))}" in checks)
        # a reading of question words as source values, re-checked as an ordinary request and stated
        or "semantic_alias_resolved" in checks)
    if (retried.status not in {"answered", "limited"} or not retried.evidence
            or not ranked and (retried.verification.level != "request_checked"
                               or "request_alignment" not in retried.verification.checks)):
        return None
    return retried.model_copy(update={"verification": retried.verification.model_copy(update={
        "checks": list(dict.fromkeys([*retried.verification.checks, "plan_replanned"]))})})


def missing_plan_answer(question):
    return QuestionAnswer(question=question, answer="질문에 맞는 계산 계획을 다시 확인합니다.",
        status="insufficient_evidence", confidence=0, selected_tools=["intent_resolution"], evidence=[], limitations=[])


def unavailable_plan(question):
    return QuestionAnswer(question=question, answer="요청한 대상·조건과 실행 계획을 원본에 대조하지 못했습니다.",
        status="insufficient_evidence", confidence=0, selected_tools=["plan_validation"],
        evidence=[], limitations=["계획 재검증이 끝나지 않아 생성 답변으로 대체하지 않았습니다."])
