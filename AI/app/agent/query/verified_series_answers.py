"""A trend or extreme question the series route could not bind is answered by the insight that states it.

"공기질 좋음 비율 추이 알려줘" names the series the insight report already computed from the
source ("공기질이 '좋음'인 날의 비율: 1999년 34.1%에서 …"). When exactly one such fact matches
the question best, it is the answer, with its cited cells; otherwise the original refusal stands.
"""
from app.agent.query.metric_observation_render import _evidence
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.references import normalize_reference
from app.agent.query.verified_facts import build_verified_question_context
from app.agent.query.verified_insight_answers import _asked_line
from app.agent.query.verified_insight_constraints import insight_intent_matches
from app.agent.query.verified_insight_matching import MIN_RELEVANCE_SCORE, verified_insight_score


def verified_series_answer(question, summary, index):
    if summary is None or index is None:
        return None
    ranked = []
    for order, item in enumerate(build_verified_question_context(summary)["insights"]):
        if item["category"] not in {"change", "trend"} or not insight_intent_matches(question, item):
            continue
        if (score := verified_insight_score(question, question, item)) >= MIN_RELEVANCE_SCORE:
            ranked.append((score, -order, item))
    ranked.sort(key=lambda candidate: candidate[:2], reverse=True)
    if not ranked or len(ranked) > 1 and ranked[0][0] == ranked[1][0]:
        return None  # nothing, or two series the question fits equally
    item = ranked[0][2]
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    cited = [cells.get(reference) for reference in item["support_references"] if ":" not in reference]
    if not cited or None in cited:
        return None
    return QuestionAnswer(
        question=question, answer=_asked_line(question, item["fact"]), status=QuestionAnswerStatus.ANSWERED,
        confidence=min(float(item.get("confidence") or 1.0), 1.0), selected_tools=["verified_series"],
        evidence=[_evidence(cell) for cell in cited], limitations=[],
        verification=QuestionAnswerVerification(level="source_checked", checks=["cited_cells", "verified_insight_fact"]))
