"""Execute only explicit table/column plans after checking the source cells."""
from app.agent.query.models import (
    QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification, QuestionVerificationLevel,
)
from app.agent.query.tabular_binding import bind_tabular_plan
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_labelled_rows import label_column, labelled_text
from app.agent.query.tabular_misread import misread
from app.agent.query.tabular_subtotal_rows import typed_total, without_subtotals
from app.agent.query.tabular_named_scope import named_column_scope
from app.agent.query.tabular_results import aggregate_text, query_evidence, scope_description
from app.agent.query.tabular_request_scope import request_matches_plan, rows_match_explicit_ranges
from app.agent.query.tabular_validation import filtered_rows, ordered_rows, query_columns, validated_table
from app.agent.query.tabular_feature_contract import feature_contract_matches, has_bounded_features
from app.agent.query.tabular_scope_conflicts import needed_columns, plan_scope_conflict
from app.agent.query.tabular_population_context import NumericPopulationContext, population_controls


def execute_tabular_query(plan, summary, data_index, question: str, intent=None) -> QuestionAnswer | None:
    if plan is None:
        return None
    tables = build_query_tables(summary)
    matches = [table for table in tables if table.id == plan.table_id]
    if len(matches) != 1:
        return None
    table = matches[0]
    plan = bind_tabular_plan(plan, table)
    if plan is not None:
        plan = named_column_scope(question, plan, table, tables)
    if plan is None or not feature_contract_matches(plan, table):
        return None
    by_id = {column.id: column for column in table.columns}
    selected = query_columns(plan, table)
    if selected is None or (not selected and plan.operation != "row_count"):
        return None
    filters = plan.filters or []
    needed = needed_columns(plan, selected) | population_controls(plan, table)
    if not needed <= by_id.keys() or plan_scope_conflict(question, plan, table, tables, needed) is not None:
        return None
    bounded_query = has_bounded_features(plan)
    fully_indexed = validated_table(table, data_index, needed)
    if getattr(data_index, "source_provider", None) is not None and (
        not table.complete or (data_index.truncated_for({table.sheet_name}) and not fully_indexed)
        or bounded_query and not fully_indexed
    ):
        from app.agent.query.streaming_tabular import execute_streaming_tabular
        return execute_streaming_tabular(plan, table, tables, data_index, question, intent)
    if not fully_indexed or not request_matches_plan(question, plan, table, tables, intent):
        return None
    if bounded_query and plan.order_by and plan.limit and not plan.group_by and (
            found := filtered_rows(table, filters, plan.filter_expression)) is not None and (
            shown := ordered_rows(found, plan)) is not None and misread(question, plan, table, found, shown, selected):
        return None  # the top rows of a table whose shown values repeat: left to the calculation
    if bounded_query:
        from app.agent.query.indexed_accumulation_execution import execute_indexed_accumulation
        return execute_indexed_accumulation(plan, table, selected, needed, question, data_index)
    rows = filtered_rows(table, filters, plan.filter_expression)
    if rows is None:
        return None
    matched, rows = rows, ordered_rows(rows, plan)
    if rows is None or misread(question, plan, table, matched, rows, selected):
        return None  # left to the calculation over the whole table
    if not rows_match_explicit_ranges(question, table, selected, rows):
        return None
    subtotal_notes = []
    if plan.operation == "numeric_summary":
        rows, subtotal_notes = without_subtotals(rows, selected, table.sheet_name)
    population = NumericPopulationContext(plan, table)
    if plan.operation == "numeric_summary" and (total := typed_total(rows, selected)):  # 790.8 = the gases above it
        rows = [row for row in rows if row is not total]
        subtotal_notes.append(f"{table.sheet_name}!{selected[0]}{total.row_number}은(는) 위 행들을 더한 합계 행이라 "
                              "중복 합산하지 않았습니다. 결과는 그 합계 행의 값과 같습니다.")
    if not all(population.add(row) for row in rows):
        return population.unavailable(question)
    if plan.operation == "lookup" and (plan.limit is not None or plan.order_by):
        # A sorted first row is not an exact record lookup; it can hide duplicates
        # or a missing identity condition.
        return None
    label = label_column(plan, table, rows)
    text, limitations = (labelled_text(label, [by_id[key] for key in selected], rows), []) if label else aggregate_text(
        plan.operation, [by_id[key] for key in selected], rows, plan.statistic,
    )
    if not text:
        return None
    limitations = [*limitations, *subtotal_notes]
    text = scope_description(plan, table) + population.description() + text
    if data_index.truncated_for({table.sheet_name}):
        limitations.append("이 표의 셀은 모두 대조했지만 같은 시트의 일부 다른 셀은 검색 범위에서 제외되었습니다.")
    if table.excluded_rows:
        text += f"\n숨겨진 {len(table.excluded_rows)}개 행은 제외한 결과입니다."
    include_identity = bool(filters) or label is not None or plan.operation == "row_count" or any(
        row.values[column] in (None, "") for row in rows for column in selected
    )
    evidence = query_evidence(table, needed, rows, include_identity)
    return QuestionAnswer(
        question=question, answer=text,
        status=QuestionAnswerStatus.LIMITED if limitations else QuestionAnswerStatus.ANSWERED,
        confidence=0.9 if limitations else 1.0,
        selected_tools=["tabular_query"], evidence=evidence, limitations=limitations,
        verification=QuestionAnswerVerification(
            level=QuestionVerificationLevel.REQUEST_CHECKED,
            checks=["source_values", "table_scope", "request_alignment", "calculation",
                    *(["column_summaries"] if plan.operation == "numeric_summary" and plan.statistic == "all"
                      and len(selected) > 1 and not plan.group_by else [])],
        ),
    )
