"""Do not replace a failed scoped query with an unrelated workbook overview."""
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus
from app.agent.query.tabular_execution import execute_tabular_query
from app.agent.query.tabular_named_fallback import named_frequency_answer
from app.agent.query.ranked_group_answers import ranked_group_answer
from app.agent.query.tabular_partial_categories import partial_category_answer
from app.agent.query.tabular_scope_conflicts import scope_clarification


def planned_tabular_answer(intent, summary, data_index, question):
    if intent.tabular_query is None:
        return None
    answer = execute_tabular_query(intent.tabular_query, summary, data_index, question, intent)
    if answer is not None:
        return answer
    if clarification := scope_clarification(intent.tabular_query, summary, data_index, question):
        return clarification
    partial = partial_category_answer(intent, summary, data_index, question)
    if partial is not None:
        return partial
    if named := named_frequency_answer(intent.tabular_query, summary, data_index, question):
        return named
    if ranked := ranked_group_answer(intent.tabular_query, summary, data_index, question, intent.targets):
        return ranked
    return QuestionAnswer(
        question=question,
        answer=(
            "요청한 집계의 대상 열·조건·전체 행을 원본과 확정하지 못했습니다. "
            "다른 항목의 요약으로 대신하지 않았습니다. "
            "집계할 시트와 열 이름을 지정해 주세요."
        ),
        status=QuestionAnswerStatus.INSUFFICIENT_EVIDENCE,
        confidence=0,
        selected_tools=["tabular_query"],
        evidence=[],
        limitations=[UNVERIFIED_PLAN],
    )


UNVERIFIED_PLAN = "집계 실행 계획을 원본 표 전체와 대조하지 못했습니다."
UNPROVEN_NOTE = "계산 계획을 원본 표와 대조하지 못해, 검색한 원본 셀을 바탕으로 작성한 답변입니다. 원본 셀에서 확인되지 않는 수치는 표시하지 않았습니다."


def unverified_plan(answer):
    """The generic refusal of a plan the validators could not prove (not a source refusal)."""
    return (answer is not None and answer.selected_tools == ["tabular_query"]
            and answer.status == "insufficient_evidence" and answer.limitations == [UNVERIFIED_PLAN])


def unproven_note(answer):
    """A generated answer that replaced an unproven plan says so and never claims request checks."""
    if answer.status == "insufficient_evidence" or UNPROVEN_NOTE in answer.limitations:
        return answer
    status = "limited" if answer.status == "answered" else answer.status
    return answer.model_copy(update={"limitations": [*answer.limitations, UNPROVEN_NOTE], "status": status})
