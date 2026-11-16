"""Route source-verified rankings and trajectories before scalar ambiguity."""
from app.agent.query.change_ranking_answers import ranked_change_answer
from app.agent.query.single_series_extreme_answers import single_series_extreme_answer
from app.agent.query.trend_answers import trend_answer
from app.agent.query.stored_ratio_phrases import stored_ratio_question
from app.agent.query.models import QuestionAnswerStatus
from app.agent.query.verified_series_answers import verified_series_answer


def time_series_answer(question, summary, index):
    effective = stored_ratio_question(question, summary)
    ranked = ranked_change_answer(effective, summary, index)
    extreme = None if ranked is not None else single_series_extreme_answer(effective, summary, index)
    answer = ranked if ranked is not None else extreme if extreme is not None else trend_answer(
        effective, summary, index,
    )
    if (answer is not None and answer.status == QuestionAnswerStatus.INSUFFICIENT_EVIDENCE
            and not answer.evidence and not answer.clarification_options):
        # The series could not be bound here; an insight that already states it may answer.
        answer = verified_series_answer(question, summary, index) or answer
    return answer.model_copy(update={"question": question}) if answer is not None and effective != question else answer
