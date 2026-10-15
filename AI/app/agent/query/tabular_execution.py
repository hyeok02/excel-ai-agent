"""Execute only explicit table/column plans after checking the source cells."""
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_results import aggregate_text, query_evidence
from app.agent.query.tabular_validation import filtered_rows, query_columns, validated_table


def execute_tabular_query(plan, summary, data_index, question: str) -> QuestionAnswer | None:
    if plan is None:
        return None
    matches = [table for table in build_query_tables(summary) if table.id == plan.table_id]
    if len(matches) != 1:
        return None
    table = matches[0]
    plan = bind_tabular_plan(plan, table)
    if plan is None:
        return None
    by_id = {column.id: column for column in table.columns}
    selected = query_columns(plan, table)
    if selected is None or (not selected and plan.operation != "row_count"):
        return None
    filters = plan.filters or []
    needed = set(selected) | {condition.column_id for condition in filters}
    if not needed <= by_id.keys() or not validated_table(table, data_index, needed):
        return None
    rows = filtered_rows(table, filters)
    if rows is None:
        return None
    text, limitations = aggregate_text(plan.operation, [by_id[key] for key in selected], rows)
    if not text:
        return None
    if data_index.truncated_for({table.sheet_name}):
        limitations.append("이 표의 셀은 모두 대조했지만 같은 시트의 일부 다른 셀은 검색 범위에서 제외되었습니다.")
    if table.excluded_rows:
        text += f"\n숨겨진 {len(table.excluded_rows)}개 행은 제외한 결과입니다."
    include_identity = bool(filters) or plan.operation == "row_count" or any(
        row.values[column] in (None, "") for row in rows for column in selected
    )
    evidence = query_evidence(table, needed, rows, include_identity)
    return QuestionAnswer(
        question=question, answer=text,
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        confidence=0.9 if limitations else 1.0,
        selected_tools=["tabular_query"], evidence=evidence, limitations=limitations,
    )
