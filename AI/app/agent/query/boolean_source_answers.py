"""Bounded model-free boolean queries; proposed numbers are never accepted."""
import re

from app.agent.query.boolean_filter_language import boolean_question, parse_boolean
from app.agent.query.models import QuestionAnswer
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_query_models import TabularQueryPlan
from app.agent.query.tabular_request_literals import source_headers
from app.agent.query.tabular_request_operations import STATISTICS, _COUNT


def boolean_source_answer(question, summary, index, intent=None):
    if not boolean_question(question):
        return None
    results = []
    for table in build_query_tables(summary):
        parsed = parse_boolean(question, table)
        if parsed is None:
            continue
        named = {column for column, _ in source_headers(parsed.remainder, table)}
        groups = [column.id for column in table.columns if re.search(
            rf"{re.escape(column.header)}\s*별|\bby\s+{re.escape(column.header)}\b", parsed.remainder, re.I)]
        selected = [column.id for column in table.columns if column.id in named and column.id not in groups]
        statistics = {kind for kind, pattern in STATISTICS.items() if re.search(pattern, parsed.remainder, re.I)}
        if re.search(_COUNT, parsed.remainder, re.I) and not statistics - {"sum"}:
            operation, selected, statistic = "row_count", [], "all"
        elif len(statistics) == 1 and selected:
            operation, statistic = "numeric_summary", next(iter(statistics))
        elif selected and re.search(r"목록|보여|\b(?:list|show)\b", parsed.remainder, re.I):
            operation, statistic = "row_list", "all"
        else:
            continue
        try:
            plan = TabularQueryPlan(operation=operation, table_id=table.id, column_ids=selected,
                group_by=groups, filters=parsed.filters, filter_expression=parsed.expression, statistic=statistic)
            answer = execute_tabular_query(plan, summary, index, question)
        except ValueError:
            continue
        if answer is not None:
            results.append(answer)
    if len(results) == 1:
        return results[0]
    if not results and intent is not None and getattr(intent, "tabular_query", None) is not None:
        results = _model_candidates(question, summary, index, intent)
        if len(results) == 1:
            return results[0]
    reason = ("조건에 맞는 원본 표가 여러 개입니다. 시트·표 범위를 지정해 주세요." if len(results) > 1 else
              "OR·제외·괄호 조건을 원본 항목과 모두 대조하지 못했습니다. 열 이름과 조건을 명시해 주세요. "
              "일부 조건만 적용하거나 OR를 AND로 바꿔 답하지 않았습니다.")
    return QuestionAnswer(question=question, answer=reason, status="insufficient_evidence", confidence=0,
                          selected_tools=["clarify_source_scope" if len(results) > 1 else "boolean_filter_query"],
                          evidence=[], limitations=[reason])


def _model_candidates(question, summary, index, intent):
    """The model's table ID cannot select one of equally matching source tables."""
    plan = intent.tabular_query
    tables = build_query_tables(summary)
    sources = [table for table in tables if table.id == plan.table_id]
    if len(sources) != 1 or len(tables) > 64:
        return []
    labels = {column.id: column.header for column in sources[0].columns}
    label = lambda key: labels.get(key, key)
    results = []
    for table in tables:
        candidate = plan.model_copy(update={
            "table_id": table.id, "column_ids": [label(key) for key in plan.column_ids],
            "group_by": [label(key) for key in plan.group_by],
            "identity_column_ids": [label(key) for key in plan.identity_column_ids],
            "order_by": label(plan.order_by) if plan.order_by else None,
            "filters": [item.model_copy(update={"column_id": label(item.column_id)}) for item in plan.filters],
            "having": [item.model_copy(update={"column_id": label(item.column_id) if item.column_id else None})
                       for item in plan.having],
        })
        answer = execute_tabular_query(candidate, summary, index, question, intent)
        if answer is not None:
            results.append(answer)
    return results
