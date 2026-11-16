"""Verified facts are matched by what they say, not by how a question or a model words it."""
from app.agent.query.source_claims import _quotes
from app.agent.query.verified_insight_answers import _asked_line
from app.agent.query.verified_insight_constraints import insight_intent_matches
from app.agent.query.verified_insight_matching import verified_insight_score

FACT = ("천식 발작 경험 비율: 1997년 5.5%에서 2024년 3.6%로 1.9%p 감소했습니다.\n"
        "최근 구간은 2023년 3.3%에서 2024년 3.6%로 0.3%p 증가했습니다.\n"
        "가장 높았던 시점은 2002년 5.8%, 가장 낮았던 시점은 2021년 2.6%입니다.")
ITEM = {"title": "천식 발작 경험 비율 변화", "topic": "Asthma Attack Prevalence", "category": "change", "fact": FACT}


def test_a_series_fact_answers_its_highest_or_lowest_point_in_any_tense():
    for question in ("천식 비율이 가장 높은 해는?", "천식 비율이 가장 낮은 연도는?"):
        assert verified_insight_score(question, question, ITEM) >= 8 and insight_intent_matches(question, ITEM)
    assert _asked_line("천식 비율이 가장 높은 해는?", FACT) == (
        "천식 발작 경험 비율: 가장 높았던 시점은 2002년 5.8%, 가장 낮았던 시점은 2021년 2.6%입니다.")


def test_what_a_fact_does_not_say_or_whom_it_is_not_about_still_does_not_match():
    assert verified_insight_score("천식 비율 평균은?", "천식 비율 평균은?", ITEM) == 0
    assert verified_insight_score("보험 가장 높은 해는?", "보험 가장 높은 해는?", ITEM) == 0
    assert not insight_intent_matches("천식 비율 알려줘", ITEM)  # a snapshot request is not the series


def test_a_claim_quotes_the_fact_or_one_line_of_it_word_for_word_only():
    assert _quotes(FACT, FACT) and _quotes("가장 높았던 시점은 2002년 5.8%, 가장 낮았던 시점은 2021년 2.6%입니다.", FACT)
    assert _quotes("천식 발작 경험 비율: 가장 높았던 시점은 2002년 5.8%, 가장 낮았던 시점은 2021년 2.6%입니다.", FACT)
    assert not _quotes("천식 발작 경험 비율: 가장 높았던 시점은 2002년 5.9%, 가장 낮았던 시점은 2021년 2.6%입니다.", FACT)
    assert not _quotes("천식 발작 경험 비율", FACT)
