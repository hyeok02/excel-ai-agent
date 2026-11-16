"""Route source-verified rankings and trajectories before scalar ambiguity."""
from app.agent.query.change_ranking_answers import ranked_change_answer
from app.agent.query.single_series_extreme_answers import single_series_extreme_answer
from app.agent.query.trend_answers import trend_answer
from app.agent.query.stored_ratio_phrases import stored_ratio_question
from app.agent.query.series_binding import is_unbound, refused_without_basis
from app.agent.query.verified_series_answers import named_series_answer, verified_series_answer


def time_series_answer(question, summary, index):
    # A series this stage could not bind is left to planning and the checked
    # draft; series_attempt's refusal is restored if they cannot answer either.
    answer = series_attempt(question, summary, index)
    return None if is_unbound(answer) else answer


def series_attempt(question, summary, index):
    effective = stored_ratio_question(question, summary)
    ranked = ranked_change_answer(effective, summary, index)
    extreme = None if ranked is not None else single_series_extreme_answer(effective, summary, index)
    answer = ranked if ranked is not None else extreme if extreme is not None else trend_answer(
        effective, summary, index,
    )
    if refused_without_basis(answer):
        # The series could not be bound here; an insight that already states it may answer.
        answer = verified_series_answer(question, summary, index) or named_series_answer(question, summary, index) or answer
    return answer.model_copy(update={"question": question}) if answer is not None and effective != question else answer
