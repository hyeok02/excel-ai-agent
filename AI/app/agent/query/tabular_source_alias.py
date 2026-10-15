"""Expose a model-selected source label as a limited, explicit interpretation."""
import re
from types import SimpleNamespace

from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.metric_observation_cells import metric_label_matches
from app.agent.query.metric_request_coverage import uncovered_request_tokens
from app.agent.query.models import QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_request_predicates import normalize

_QUALIFIER = re.compile(
    r"아닌|아니|제외|이상|이하|초과|미만|보다|평균|합계|총합|비교|증감|증가|감소|비율|"
    r"퍼센트|백만|전년|작년|올해|현재|최근|최신|각각|모두|전체|모든|합쳐|외국|국내|해외"
)


def source_label_alias_answer(question, summary, data_index, intent, clarification):
    """Only retry an otherwise ambiguous scalar lookup; never create a plan."""
    request = alias_lookup_request(question, summary, intent, clarification)
    if request is None:
        return None
    subject, remainder, table, plan = request
    condition = plan.filters[0]
    label = condition.value
    if not re.fullmatch(r"[A-Za-z][A-Za-z .&'()-]{1,79}", label):
        return None
    rows = [row for row in table.rows if isinstance(row.values[condition.column_id], str)
            and normalize(row.values[condition.column_id]) == normalize(label)]
    if len(rows) != 1:
        return None
    rewritten = f"{subject}({label}) {remainder}"
    if ambiguous_source_answer(rewritten, summary, data_index, intent) is not None:
        return None
    answer = execute_tabular_query(plan, summary, data_index, rewritten, intent)
    if answer is None or answer.verification.level != QuestionVerificationLevel.REQUEST_CHECKED:
        return None
    explanation = (f"질문의 대상 ‘{subject}’에 대응하는 원본 항목을 ‘{label}’로 해석해 조회했습니다. "
                   "두 명칭의 의미가 같은지는 원본에서 확인하지 못했습니다.")
    return answer.model_copy(update={
        "question": question, "resolved_question": rewritten,
        "answer": explanation + "\n" + answer.answer,
        "status": QuestionAnswerStatus.LIMITED, "confidence": min(answer.confidence, 0.7),
        "limitations": [*answer.limitations, "질문의 대상 명칭과 원본 명칭의 대응은 모델 해석입니다."],
        "verification": QuestionAnswerVerification(
            level=QuestionVerificationLevel.SOURCE_CHECKED,
            checks=[check for check in answer.verification.checks if check != "request_alignment"]
            + ["semantic_alias_resolved"],
        ),
    })


def alias_lookup_request(question, summary, intent, clarification):
    plan = intent.tabular_query
    if ("clarify_source_scope" not in clarification.selected_tools
            or clarification.status != QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
            or not intent.from_model or intent.whole_workbook or intent.kind != "cell_lookup"
            or intent.relational_query or intent.header_relation or plan is None
            or plan.operation != "lookup" or plan.column_scope != "selected"
            or plan.limit or plan.order_by or len(plan.filters) != 1
            or not re.fullmatch(r"[가-힣\s?]+", question)):
        return None
    target = re.match(r"^(?P<subject>[가-힣]{2,30}?)(?:의|은|는)?\s+(?P<metric>.+)$", question)
    if target is None or _QUALIFIER.search(question):
        return None
    subject, remainder = target.group("subject"), target.group("metric")
    if re.search(r"[가-힣]+(?:과|와)\s|및|그리고|하고", remainder):
        return None
    tables = build_query_tables(summary)
    matches = [table for table in tables if table.id == plan.table_id]
    if len(matches) != 1 or (plan := bind_tabular_plan(plan, matches[0])) is None:
        return None
    table = matches[0]
    condition = plan.filters[0]
    label = condition.value
    if (condition.operator != "equals" or not isinstance(label, str)
            or not plan.column_ids or condition.column_id in plan.column_ids
            or table.hidden_columns & (set(plan.column_ids) | {condition.column_id})):
        return None
    # A Korean label actually present in the source takes precedence over a
    # model-proposed translation to a different, English-labeled record.
    if any(isinstance(value, str) and normalize(value) == normalize(subject)
           for candidate in tables for row in candidate.rows for value in row.values.values()):
        return None
    columns = [column for column in table.columns if column.id in plan.column_ids]
    if not all(metric_label_matches(column.header, remainder) for column in columns):
        return None
    observations = [SimpleNamespace(label=SimpleNamespace(value=column.header), entity_cells=())
                    for column in columns]
    if uncovered_request_tokens(remainder, observations, set()):
        return None
    return subject, remainder, table, plan
