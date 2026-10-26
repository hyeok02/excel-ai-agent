"""Use bounded group/rank reducers for fully source-validated indexed tables."""
from app.agent.query.streaming_tabular_boundaries import ambiguous_boundary
from app.agent.query.streaming_tabular_results import result_for, stream_answer
from app.agent.query.streaming_tabular_rows import row_eligible
from app.agent.query.tabular_request_scope import rows_match_explicit_ranges
from app.agent.query.tabular_population_context import NumericPopulationContext, numeric_population


def execute_indexed_accumulation(plan, table, selected, needed, question, index):
    result = result_for(plan, table, selected)
    if result is None:
        return None
    numeric_columns = set()
    population = NumericPopulationContext(plan, table)
    result.hidden = len(table.excluded_rows)
    for row in table.rows:
        if ambiguous_boundary(row, table, numeric_columns, allow_totals=numeric_population(plan)):
            return None
        result.population += 1
        accepted = row_eligible(row, plan, table)
        if accepted is None:
            return None
        if accepted:
            if not population.add(row):
                return population.unavailable(question)
            if any(row.formulas.get(column) and row.values[column] is None for column in needed):
                return None
            if not rows_match_explicit_ranges(question, table, needed, [row]) or not result.add(row):
                return None
    answer = stream_answer(question, table, needed, result, source_scanned=False)
    if answer is not None:
        answer.answer = population.description() + answer.answer
    if answer is not None and index.truncated_for({table.sheet_name}):
        answer.limitations.append("이 표의 셀은 모두 대조했지만 같은 시트의 일부 다른 셀은 검색 범위에서 제외되었습니다.")
        answer.status, answer.confidence = "limited", 0.9
    return answer
