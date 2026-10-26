"""Explain an incompatible source meaning before any generated fallback."""
from app.agent.query.metric_observation_cells import _numeric, metric_label_matches
from app.agent.query.metric_observations import horizontal_observations
from app.agent.query.metric_semantics import column_metric_conflict, column_metric_matches, people_number_formats
from app.agent.query.metric_row_semantics import row_metric_column
from app.agent.query.models import QuestionAnswer, QuestionAnswerEvidence
from app.agent.query.tabular_catalog import build_query_tables
from app.services.provenance import EvidenceKind


def incompatible_metric_answer(question, summary, index):
    tables = build_query_tables(summary)
    conflicts = [column for table in tables for column in table.columns
                 if metric_label_matches(column.header, question) and column_metric_conflict(column, question)]
    raw_points = horizontal_observations(index.rows, question, include_conflicts=True)
    checked = set()
    for point in raw_points:
        if point.label.reference in checked:
            continue
        checked.add(point.label.reference)
        rows = [row for row in index.rows if row.sheet_name == point.label.sheet_name]
        axis = next(row for row in rows if any(cell.reference == point.period_cell.reference for cell in row.cells))
        column = row_metric_column(point.label, axis, rows)
        if column_metric_conflict(column, question):
            conflicts.append(column)
    if not conflicts:
        return None
    if any(column_metric_matches(column, question) and any(_numeric(value) for value in column.sample_values)
           for table in tables for column in table.columns):
        return None
    # Horizontal financial reports can coexist with category tables. Their
    # explicit measure label and numeric row must remain available to routing.
    conflicting_refs = {column.header_reference for column in conflicts}
    if any(point.label.reference not in conflicting_refs
           for point in horizontal_observations(index.rows, question)):
        return None
    column = conflicts[0]
    context = " / ".join(dict.fromkeys(text for _, text in column.context))
    units = people_number_formats(column)
    meaning = (f"표시 형식 ‘{' / '.join(units)}’의 인원 값" if units else f"‘{context}’ 아래의 분류 항목")
    refs = [(column.header_reference, column.header), *column.context]
    evidence = [QuestionAnswerEvidence(
        kind=EvidenceKind.CELL, sheet_name=ref.rsplit("!", 1)[0], reference=ref.rsplit("!", 1)[1],
        value=value, description="원본 항목과 상위 분류", label="원본 항목 의미",
    ) for ref, value in dict(refs).items()]
    return QuestionAnswer(
        question=question, status="insufficient_evidence", confidence=0,
        answer=(f"요청한 지표를 확인하지 못했습니다. 원본의 ‘{column.header}’는 {meaning}이므로, "
                "이름이 비슷한 다른 지표로 바꾸어 답하지 않았습니다. "
                "원하는 금액 지표가 있는 표를 지정하거나 해당 분류의 인원을 질문해 주세요."),
        selected_tools=["check_metric_semantics"], evidence=evidence,
        limitations=["원본 항목의 분류와 질문에서 요청한 지표의 의미가 일치하지 않습니다."],
    )
