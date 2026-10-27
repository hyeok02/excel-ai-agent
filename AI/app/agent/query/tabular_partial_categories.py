"""Offer annotated-category matches without certifying inferred category meaning."""
import re

from app.agent.query.models import QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_request_literals import source_headers
from app.agent.query.tabular_request_predicates import categorical_predicates, normalize


def partial_category_answer(intent, summary, data_index, question):
    plan = intent.tabular_query
    if (plan is None or getattr(plan, "filter_expression", None) is not None
            or plan.operation != "row_list" or plan.limit or plan.order_by
            or re.search(r"정확|완전히|동일|일치|\bexact(?:ly)?\b", question, re.I)):
        return None
    tables = [table for table in build_query_tables(summary) if table.id == plan.table_id]
    if len(tables) != 1 or (plan := bind_tabular_plan(plan, tables[0])) is None:
        return None
    table = tables[0]
    candidates = [item for item in plan.filters if item.operator == "contains"]
    if len(candidates) != 1:
        return None
    condition = candidates[0]
    value = condition.value
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z가-힣][A-Za-z가-힣 ]{1,39}", value):
        return None
    headers = source_headers(question, table)
    predicate = (condition.column_id, ("str", normalize(value)), "equals")
    if categorical_predicates(question, headers).count(predicate) != 1:
        return None
    source_values = {str(row.values[condition.column_id]).strip() for row in table.rows
                     if isinstance(row.values[condition.column_id], str)}
    matching = {source for source in source_values if value.casefold() in source.casefold()}
    annotated = re.compile(rf"{re.escape(value)}\s*\([^()]+\)", re.I)
    if not matching or not all(annotated.fullmatch(source) for source in matching):
        return None
    column = next(column for column in table.columns if column.id == condition.column_id)
    rewritten = _contains_question(question, column.header, value)
    if rewritten is None:
        return None
    # All untouched conditions, source scopes, cells, and complete populations
    # still pass the ordinary deterministic executor. Never relax its guards.
    answer = execute_tabular_query(plan, summary, data_index, rewritten, intent)
    if answer is None or answer.verification.level != QuestionVerificationLevel.REQUEST_CHECKED:
        return None
    examples = ", ".join(f"‘{source}’" for source in sorted(matching)[:5])
    explanation = (
        f"‘{column.header}’에 ‘{value}’와 정확히 같은 값은 없고 {examples}처럼 설명이 붙어 있습니다. "
        f"‘{value}’를 포함하는 원문을 찾은 결과입니다. 같은 의미의 분류인지는 확인하지 않았습니다."
    )
    return answer.model_copy(update={
        "question": question, "resolved_question": rewritten,
        "answer": explanation + "\n" + answer.answer,
        "status": QuestionAnswerStatus.LIMITED, "confidence": min(answer.confidence, 0.7),
        "limitations": [*answer.limitations, "범주 의미의 동일성이 아니라 표시된 원문의 부분 일치만 확인했습니다."],
        "verification": QuestionAnswerVerification(
            level=QuestionVerificationLevel.SOURCE_CHECKED,
            checks=[check for check in answer.verification.checks if check != "request_alignment"]
            + ["category_match_interpreted"],
        ),
    })


def _contains_question(question, header, value):
    quoted = rf"(?:'{re.escape(value)}'|\"{re.escape(value)}\"|‘{re.escape(value)}’|“{re.escape(value)}”|{re.escape(value)})"
    pattern = re.compile(
        rf"{re.escape(header)}\s*(?:이|가|은|는)?\s*{quoted}(?=(?:인|이고|이며)(?:\s|$))", re.I,
    )
    matches = list(pattern.finditer(question))
    if len(matches) != 1:
        return None
    match = matches[0]
    return question[:match.start()] + f"{header} contains '{value}'" + question[match.end():]
