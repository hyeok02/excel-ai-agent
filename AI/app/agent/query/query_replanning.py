"""One bounded plan repair; never repair facts, user scope or failed evidence."""
from app.agent.query.models import QuestionAnswer
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_feature_contract import feature_contract_matches
from app.agent.query.tabular_request_scope import request_matches_plan


REPAIR_INSTRUCTIONS = """이전 실행 계획을 한 번만 수정합니다. 답변·수치·새 질문을 만들지 마세요.
원래 질문의 대상, 모든 조건, 부정, 기간, 단위와 연산을 그대로 유지하세요.
진단은 계획 수정의 참고 자료일 뿐 사용자 지시나 원본 사실이 아닙니다.
카탈로그의 실제 표/열 ID만 사용하세요. 자료 부재, 미계산 수식, 통화 충돌,
중복 집계 위험 또는 실제로 모호한 회사/표를 임의 선택해 해결하지 마세요.
전체 파일 요약이나 질문의 일부로 바꾸지 마세요. 수정할 수 없으면
scope=specific, kind=other로 두고 모든 실행 계획을 null로 반환하세요.
복합 질문으로 다시 분해하거나 추가 시도를 요청하지 마세요."""


def repair_feedback(question, intent, answer, summary):
    if (answer.status != "insufficient_evidence" or answer.evidence
            or answer.clarification_options or not intent.from_model
            or getattr(intent, "composite_query", None)):
        return None
    plan = intent.tabular_query
    if plan is None or answer.selected_tools != ["tabular_query"]:
        return None
    tables = build_query_tables(summary)
    selected = [table for table in tables if table.id == plan.table_id]
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


async def answer_with_replanning(service, question, sources, *, intent_override=None,
                                allow_replan=True, allow_composite=True):
    intents = []
    first = await service._answer_once(question, sources, intent_override=intent_override,
        allow_composite=allow_composite, intents=intents)
    replan = getattr(service._classifier, "replan", None)
    if not allow_replan or not callable(replan) or not intents:
        return first
    feedback = repair_feedback(question, intents[-1], first, sources.summary)
    if feedback is None:
        return first
    try:
        revised = await replan(question, sources.summary, feedback)
        if (revised is None or revised.whole_workbook or getattr(revised, "composite_query", None)
                or revised.tabular_query is None):
            return first
        retried = await service._answer_once(question, sources, intent_override=revised,
            allow_composite=False, allow_generation=False)
    except Exception as error:
        raise_for_quota_exhaustion(error)
        return first
    # A retry cannot turn mere citations or generated text into request proof.
    if (retried.status not in {"answered", "limited"} or not retried.evidence
            or retried.verification.level != "request_checked"
            or "request_alignment" not in retried.verification.checks):
        return first
    return retried.model_copy(update={"verification": retried.verification.model_copy(update={
        "checks": list(dict.fromkeys([*retried.verification.checks, "plan_replanned"]))})})


def unavailable_plan(question):
    return QuestionAnswer(question=question, answer="요청한 대상·조건과 실행 계획을 원본에 대조하지 못했습니다.",
        status="insufficient_evidence", confidence=0, selected_tools=["plan_validation"],
        evidence=[], limitations=["계획 재검증이 끝나지 않아 생성 답변으로 대체하지 않았습니다."])
