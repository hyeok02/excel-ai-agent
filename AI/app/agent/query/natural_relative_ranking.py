"""Resolve a bounded colloquial rank request, exposing every semantic interpretation."""
import re

from app.agent.query.models import QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel
from app.agent.query.relative_group_ranking import relative_plan_valid
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query

_REQUEST = re.compile(
    r"\s*(?P<anchor>[^?？\n]{1,80}?)\s+(?:다음(?:으로)?|다음\s*순위로)\s*"
    r"(?P<metric>(?:가장|제일)\s*많이\s*(?:팔린|판매된)|"
    r"(?:판매\s*수량|판매량|판매\s*금액|매출액|매출)(?:이|가|\s*기준으로)?\s*"
    r"(?:가장|제일)\s*(?:많은|높은|큰))\s*"
    r"(?:품목|제품|상품|항목|분류)(?:이|은|는|가)?\s*"
    r"(?:뭐야|뭔가요|뭐예요|무엇인가요|무엇이야|알려줘|알려주세요|보여줘)?\s*[?？.!]*\s*"
)
_HEADERS = {
    "quantity": {"qty", "quantity", "units", "unitssold", "salesquantity", "quantitysold",
                 "판매수량", "판매량", "수량", "판매개수"},
    "amount": {"totalprice", "salesamount", "totalsales", "salesrevenue", "revenue",
               "매출", "매출액", "판매금액", "총판매금액"},
}
_QUALIFIER = re.compile(r"에서|만$|제외|이상|이하|미만|초과|보다|올해|작년|최근|전체|평균|합계|[0-9]")


def _normal(value):
    return re.sub(r"[\s_-]+", "", str(value)).casefold()


def _identity(value):
    return " ".join(str(value).casefold().split())


def _has_label(table, column, label):
    return any(isinstance(value, str) and _identity(value) == _identity(label)
               for value in (*column.sample_values, *(row.values.get(column.id) for row in table.rows)))


def _competing_source(tables, selected, group, metric, label):
    for table in tables:
        if table.id == selected.id:
            continue
        visible = [column for column in table.columns if column.id not in table.hidden_columns]
        if not any(_normal(column.header) in _HEADERS[metric] for column in visible):
            continue
        if any(_has_label(table, column, label) or (
                not table.complete and _normal(column.header) == _normal(group.header)) for column in visible):
            return True
    return False


def natural_relative_answer(question, summary, data_index, intent):
    """No new model call: validate its proposed IDs and compute all source rows."""
    match = _REQUEST.fullmatch(question)
    plan = intent.tabular_query
    if (match is None or plan is None or not intent.from_model or intent.whole_workbook
            or intent.kind != "aggregation" or intent.relational_query or intent.header_relation
            or plan.relative_rank is None or not relative_plan_valid(plan)
            or plan.operation != "numeric_summary" or plan.statistic != "sum"
            or plan.filters or plan.identity_column_ids or not plan.descending
            or plan.relative_rank.direction != "after"):
        return None
    tables = build_query_tables(summary)
    selected = [table for table in tables if table.id == plan.table_id]
    if len(selected) != 1 or (plan := bind_tabular_plan(plan, selected[0])) is None:
        return None
    table, subject = selected[0], match.group("anchor").strip(" '\"‘’“”")
    anchor = plan.relative_rank
    if not isinstance(anchor.value, str):
        return None
    metric = "amount" if re.search(r"금액|매출", match.group("metric")) else "quantity"
    measures = [column for column in table.columns if _normal(column.header) in _HEADERS[metric]]
    if len(measures) != 1 or plan.column_ids != [measures[0].id]:
        return None
    if table.hidden_columns & {anchor.column_id, measures[0].id}:
        return None
    # A source spelling wins over a model's proposed translation. Never discard
    # a date/filter phrase by treating a whole Korean clause as a label alias.
    alias = _identity(subject) != _identity(anchor.value)
    if alias and (not re.fullmatch(r"[가-힣]{2,20}", subject) or _QUALIFIER.search(subject)
                  or not re.fullmatch(r"[A-Za-z][A-Za-z .&'()-]{1,79}", anchor.value)):
        return None
    if alias and any(_has_label(candidate, column, subject) for candidate in tables
                     for column in candidate.columns):
        return None
    anchors = [column for column in table.columns if _has_label(table, column, anchor.value)]
    if len(anchors) != 1 or anchors[0].id != anchor.column_id:
        return None
    group, measure = anchors[0], measures[0]
    if _competing_source(tables, table, group, metric, anchor.value):
        return None
    # The full-source group accumulator also checks names outside catalog samples.
    anchor._original_request_label = subject
    rewritten = (f"{table.sheet_name} 시트 {group.header}별 {measure.header} 합계 내림차순에서 "
                 f"{anchor.value} 다음 순위")
    answer = execute_tabular_query(plan, summary, data_index, rewritten, intent)
    if answer is None or answer.verification.level != QuestionVerificationLevel.REQUEST_CHECKED:
        return None
    basis = "판매금액" if metric == "amount" else "판매수량"
    interpretation = (f"‘{subject}’를 원본 ‘{anchor.value}’로, {basis}을 ‘{measure.header}’의 합계로 "
                      f"해석했습니다. ‘{table.sheet_name}’ 시트의 ‘{group.header}’별로 비교했습니다.")
    return answer.model_copy(update={
        "question": question, "resolved_question": rewritten,
        "answer": answer.answer + "\n" + interpretation,
        "status": QuestionAnswerStatus.LIMITED, "confidence": min(answer.confidence, 0.8),
        "limitations": [*answer.limitations, "질문의 명칭과 집계 기준은 위와 같이 해석했으며, 계산은 원본 전체와 대조했습니다."],
        "verification": QuestionAnswerVerification(level=QuestionVerificationLevel.SOURCE_CHECKED,
            checks=[check for check in answer.verification.checks if check != "request_alignment"]
            + ["semantic_alias_resolved", "rank_interpretation"]),
    })
