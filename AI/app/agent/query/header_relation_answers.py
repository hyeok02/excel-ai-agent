"""Report header placement without asserting real-world identity or difference."""
from dataclasses import asdict

from app.agent.query.header_relation_binding import (
    fallback_plans, headers_in_requested_ranges, independent_mentions,
    matching_columns, relation_request, scoped_tables,
)
from app.agent.query.models import QuestionAnswer, QuestionAnswerEvidence, QuestionAnswerVerification
from app.agent.query.tabular_catalog import build_query_tables

_LIMITATION = ("열 이름과 배치만 확인한 답변입니다. 함께 적혔거나 별도 열이라는 사실만으로 "
               "실제 의미·작업 내용이 같은지 다른지는 단정할 수 없습니다.")


def header_relation_answer(question, summary, data_index, intent=None):
    if getattr(intent, "from_model", False) and getattr(intent, "kind", "other") not in {"field_relation", "other"}:
        return None
    plan = getattr(intent, "header_relation", None)
    if not relation_request(question, intent, plan.mentions if plan else ()):
        return None
    if getattr(intent, "tabular_query", None) or getattr(intent, "relational_query", None):
        return None
    tables = scoped_tables(question, build_query_tables(summary))
    cells = {cell.reference: cell for row in data_index.rows for cell in row.cells}
    if plan is None:
        plans = fallback_plans(question, tables, cells, getattr(intent, "kind", "") == "field_relation")
        if len(plans) != 1:
            return _clarify(question) if plans or getattr(intent, "kind", "") == "field_relation" else None
        plan = plans[0]
    if not independent_mentions(plan.mentions, question):
        return _clarify(question)
    if len(set(plan.column_ids)) != len(plan.column_ids):
        return _clarify(question)
    candidates = [(table, columns) for table in tables
                  for columns in matching_columns(table, plan.mentions, cells)]
    # A model picking one valid table does not disambiguate multiple source scopes.
    if len(candidates) != 1:
        return _clarify(question)
    table, columns = candidates[0]
    if (table.id != plan.table_id or set(plan.column_ids) != {column.id for column in columns}
            or not headers_in_requested_ranges(question, table, columns)):
        return _clarify(question)
    if not relation_request(question, intent, plan.mentions):
        return None
    labels = " · ".join(f"‘{column.header}’({column.header_reference})" for column in columns)
    if len(columns) == 1:
        body = f"‘{table.sheet_name}’ 시트의 {labels} 하나의 열 이름에 두 명칭이 함께 적혀 있습니다."
    else:
        body = f"‘{table.sheet_name}’ 시트에서 {labels}은 서로 다른 열로 표시되어 있습니다."
    return QuestionAnswer(
        question=question, answer=body + "\n\n" + _LIMITATION,
        status="limited", confidence=0.8, selected_tools=["inspect_header_relation"],
        evidence=[QuestionAnswerEvidence(**asdict(cells[column.header_reference].evidence()),
                  label=f"원본 열 이름: {column.header}") for column in columns],
        limitations=[_LIMITATION], verification=QuestionAnswerVerification(
            level="source_checked", checks=["cited_cells", "header_labels", "header_positions"]),
    )


def _clarify(question):
    return QuestionAnswer(
        question=question, answer="비교한 두 명칭을 하나의 원본 표에 명확히 연결하지 못했습니다. "
        "시트 이름과 두 열 이름(또는 함께 적힌 열 이름)을 지정해 주세요. "
        "이름이 비슷하거나 함께 적혀 있다는 이유로 같은 의미라고 판단하지 않겠습니다.",
        status="insufficient_evidence", confidence=0, selected_tools=["clarify_source_scope"],
        evidence=[], limitations=["열 이름의 관계를 확인할 대상이나 범위가 불명확합니다."],
    )
