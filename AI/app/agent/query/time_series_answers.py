"""Route source-verified rankings and trajectories before scalar ambiguity."""
from app.agent.query.change_ranking_answers import ranked_change_answer
from app.agent.query.trend_answers import trend_answer


def time_series_answer(question, summary, index):
    ranked = ranked_change_answer(question, summary, index)
    return ranked if ranked is not None else trend_answer(question, summary, index)
