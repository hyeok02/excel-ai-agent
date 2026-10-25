"""The app's own follow-up questions must find the insight they were made from.

Templates mirror FE questionPresentation.ts. Their request wording (관련 수치와
원본 근거, 항목별로, 시작 값과 마지막 값 기준으로) says how to show a fact; it is
never a content term the insight has to contain.
"""
from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.verified_insight_matching import MIN_RELEVANCE_SCORE, verified_insight_score
from tests.test_metric_observation_answers import _index

ITEMS = {
    "metric": {"title": "Supplier Alpha 1위", "topic": "", "category": "metric",
               "fact": "TOP HOLDERS에서 1위는 Supplier Alpha이며 비중은 8.9%입니다."},
    "summary": {"title": "주문 유형 분포", "topic": "", "category": "summary",
                "fact": "‘주문 유형’ 항목은 3가지로 나뉩니다. 일반 5건, 긴급 4건, 반품 1건입니다."},
    "change": {"title": "순이익(Net Income) 변화", "topic": "순이익(Net Income)", "category": "change",
               "fact": "순이익(Net Income): 2021년 100에서 2025년 150으로 50(50%) 증가했습니다."},
}
FOLLOW_UPS = {
    "metric": "Supplier Alpha 1위 관련 수치와 원본 근거를 보여줘",
    "summary": "주문 유형 분포를 항목별로 요약해줘",
    "change": "순이익(Net Income) 변화를 시작 값과 마지막 값 기준으로 비교해줘",
}


def test_each_follow_up_template_matches_its_own_insight_only():
    for kind, question in FOLLOW_UPS.items():
        assert verified_insight_score(question, question, ITEMS[kind]) >= MIN_RELEVANCE_SCORE, kind
        for other, item in ITEMS.items():
            if other != kind:
                assert verified_insight_score(question, question, item) < MIN_RELEVANCE_SCORE, (kind, other)


def test_request_wording_alone_or_another_identity_never_matches():
    question = "관련 수치와 원본 근거를 보여줘"
    assert all(verified_insight_score(question, question, item) == 0 for item in ITEMS.values())
    beta = "Supplier Beta 1위 관련 수치와 원본 근거를 보여줘"
    assert verified_insight_score(beta, beta, ITEMS["metric"]) == 0


def test_start_and_last_value_comparison_is_not_a_latest_snapshot():
    base = {"A1": "Company", "B1": "Headcount", "C1": "Headcount As Of",
            "A2": "Lumen Works", "B2": 20, "C2": "2030-10-01",
            "A3": "Lumen Works", "B3": 25, "C3": "2030-10-01"}
    index = _index({"Data": base})
    question = "Lumen Works의 Headcount 변화를 시작 값과 마지막 값 기준으로 비교해줘"
    assert metric_observation_answer(question, None, index) is None
    latest = metric_observation_answer("Lumen Works의 최신 Headcount 알려줘", None, index)
    assert latest.status == "insufficient_evidence"


def test_a_snapshot_insight_never_answers_a_change_over_time():
    from app.agent.query.verified_insight_constraints import insight_intent_matches
    multiple = {"title": "순이익 대비 인수가격: 비교군 중앙값보다 26.6% 낮음", "topic": "순이익 대비 인수가격",
                "category": "metric", "fact": "순이익 대비 인수가격은 13.57배입니다."}
    assert not insight_intent_matches("순이익 처음과 마지막 비교해줘", multiple)
    assert insight_intent_matches(f"{multiple['title']} 관련 수치와 원본 근거를 보여줘", multiple)
