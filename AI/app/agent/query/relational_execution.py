"""Safe cross-table execution without LLM-produced joins, numbers or evidence."""
from app.agent.query.models import QuestionAnswer, QuestionAnswerVerification, QuestionVerificationLevel
from app.agent.query.relational_binding import bind_relational_plan
from app.agent.query.relational_join import joined_rows
from app.agent.query.relational_models import RelationalError
from app.agent.query.relational_results import relational_evidence, relational_text
from app.agent.query.relational_scope import validate_relational_scope
from app.agent.query.tabular_catalog import build_query_tables


def relational_query_answer(plan, summary, index, question, intent=None):
    if plan is None:
        return None
    try:
        tables = build_query_tables(summary)
        plan, sides, needed = bind_relational_plan(plan, tables, index)
        validate_relational_scope(question, plan, sides, tables)
        joined, unmatched, population = joined_rows(plan, sides)
        text, limitations = relational_text(plan, sides, joined, unmatched, population)
    except RelationalError as error:
        return QuestionAnswer(question=question, answer=str(error), status="insufficient_evidence",
                              confidence=0, selected_tools=["relational_query"], evidence=[],
                              limitations=[str(error)])
    if unmatched:
        limitations.append(f"연결되지 않은 왼쪽 행 {unmatched}개를 명시했습니다. 원본에 없는 오른쪽 값은 생성하지 않았습니다.")
    return QuestionAnswer(
        question=question, answer=text, status="limited" if limitations else "answered",
        confidence=0.9, selected_tools=["relational_query"], evidence=relational_evidence(sides, needed, joined),
        limitations=limitations,
        verification=QuestionAnswerVerification(level=QuestionVerificationLevel.SOURCE_CHECKED,
            checks=["source_values", "complete_table_scan", "typed_join_keys", "join_cardinality", "calculation"]),
    )
