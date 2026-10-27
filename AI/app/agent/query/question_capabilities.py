"""Carry workbook capability boundaries through direct service callers too."""
from app.agent.query.models import QuestionAnswer
from app.services.workbook_data_model import DATA_MODEL_ONLY_MESSAGE


def unavailable_workbook_answer(question, summary):
    if not summary.data_model_only:
        return None
    return QuestionAnswer(question=question, answer=DATA_MODEL_ONLY_MESSAGE,
        status="insufficient_evidence", confidence=0, selected_tools=["check_workbook_capabilities"],
        evidence=[], limitations=list(summary.limitations))


def with_workbook_limitations(answer, summary):
    return answer.model_copy(update={"limitations": list(dict.fromkeys(
        [*answer.limitations, *summary.limitations]))})
