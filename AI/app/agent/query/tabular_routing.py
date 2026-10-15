"""Do not replace a failed scoped query with an unrelated workbook overview."""
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus
from app.agent.query.tabular_execution import execute_tabular_query


def planned_tabular_answer(intent, summary, data_index, question):
    if intent.tabular_query is None:
        return None
    answer = execute_tabular_query(intent.tabular_query, summary, data_index, question)
    if answer is not None:
        return answer
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
        limitations=["집계 실행 계획을 원본 표 전체와 대조하지 못했습니다."],
    )
