"""Route source-verified rankings and trajectories before scalar ambiguity."""
from app.agent.query.change_ranking_answers import ranked_change_answer
from app.agent.query.trend_answers import trend_answer
from app.agent.query.stored_ratio_phrases import stored_ratio_question


def time_series_answer(question, summary, index):
    effective = stored_ratio_question(question, summary)
    ranked = ranked_change_answer(effective, summary, index)
    answer = ranked if ranked is not None else trend_answer(effective, summary, index)
    return answer.model_copy(update={"question": question}) if answer is not None and effective != question else answer
