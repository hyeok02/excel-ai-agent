"""A trend or extreme question the series route could not bind is answered by the insight that states it.

"공기질 좋음 비율 추이 알려줘" names the series the insight report already computed from the
source ("공기질이 '좋음'인 날의 비율: 1999년 34.1%에서 …"). When exactly one such fact matches
the question best, it is the answer, with its cited cells; otherwise the original refusal stands.
"""
import asyncio
import re
from types import SimpleNamespace

from app.agent.query.metric_observation_render import _evidence
from app.agent.query.quota_errors import raise_for_quota_exhaustion
from app.agent.query.tabular_translated_filters import candidate_words
from app.services.insights.facts.context import build_workbook_context
from app.services.insights.narratives.all_series_facts import all_series_facts
from app.agent.query.models import QuestionAnswer, QuestionAnswerStatus, QuestionAnswerVerification
from app.agent.query.references import normalize_reference
from app.agent.query.verified_facts import build_verified_question_context
from app.agent.query.verified_insight_answers import _asked_line
from app.agent.query.verified_insight_constraints import insight_intent_matches
from app.agent.query.verified_insight_matching import MIN_RELEVANCE_SCORE, verified_insight_score

MAX_TOPICS = 250


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


def named_series_answer(question, summary, index, resolver=None):
    """"석탄 발전량 추이" names a series no card shows: the word is read among every series name.

    One series must be named; of its sections, annual totals come first, as in the report, and
    the chosen fact must be the only one there. The reading is stated with the answer.
    """
    if summary is None or index is None:
        return None
    facts = [(priority, item) for priority, item in all_series_facts(build_workbook_context(summary)) if item.topic]
    topics = list(dict.fromkeys(str(item.topic) for _, item in facts))[:MAX_TOPICS]
    words = [word for word in candidate_words(question, SimpleNamespace(columns=())) if re.search(r"[가-힣]", word)]
    if not topics or not words:
        return None
    if resolver is None:
        from app.agent.query.tabular_source_alias_resolver import LangChainSourceLabelResolver
        resolver = LangChainSourceLabelResolver.from_environment()
    if resolver is None:
        return None
    try:
        results = asyncio.run(_read(resolver, words, topics))
    except Exception as exception:
        raise_for_quota_exhaustion(exception)
        return None
    named = [(word, topics[result.candidate_id]) for word, result in zip(words, results)
             if result.status == "resolved" and type(result.candidate_id) is int and 0 <= result.candidate_id < len(topics)]
    # "발전량" inside "석탄 발전량" is the wider name: the phrase naming another series is the more specific.
    named = [(word, topic) for word, topic in named
             if not any(word != other and word in other and topic != named_topic for other, named_topic in named)]
    named = [(word, topic) for word, topic in named if not any(word != other and other in word for other, _ in named)]
    if len({topic for _, topic in named}) != 1:
        return None
    word, topic = named[0]
    chosen = [(priority, item) for priority, item in facts if str(item.topic) == topic]
    first = min(priority for priority, _ in chosen)
    stated = {item.fact: item for priority, item in chosen if priority == first}
    if len(stated) != 1:
        return None  # the same series read differently in two tables: not one answer
    item = next(iter(stated.values()))
    if not insight_intent_matches(question, item.model_dump()):
        return None  # the annual series does not state what is asked; another section never stands in
    cells = {normalize_reference(cell.reference): cell for row in index.rows for cell in row.cells}
    cited = [cells.get(normalize_reference(reference)) for reference in item.evidence if ":" not in reference]
    if not cited or None in cited:
        return None
    return QuestionAnswer(
        question=question, answer=f"해석: ‘{word}’ → {topic}\n{_asked_line(question, item.fact)}",
        status=QuestionAnswerStatus.LIMITED, confidence=0.8, selected_tools=["verified_series"],
        evidence=[_evidence(cell) for cell in cited],
        limitations=[f"질문의 표현을 원본 계열로 옮긴 해석(‘{word}’ → {topic})이 의도와 맞는지 확인해 주세요."],
        verification=QuestionAnswerVerification(level="source_checked", checks=["cited_cells", "semantic_alias_resolved"]))


async def _read(resolver, words, topics):
    return await asyncio.gather(*(resolver.resolve(word, "data series", topics) for word in words))
