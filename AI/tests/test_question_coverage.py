"""Questions asking for the top row, or naming columns in Korean, read the source the same way."""
import asyncio
from types import SimpleNamespace

from app.agent.query.intent_models import QuestionIntent
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.tabular_fixed_groups import without_fixed_groups
from app.agent.query.tabular_query_models import TabularQueryPlan
from app.agent.query.tabular_translated_filters import translated_filter_answer
from tests.tabular_query_fixtures import table_fixture

POLICIES = [["Policy", "State", "InsuredValue"], ["P1", "NY", 100], ["P2", "WI", 900], ["P3", "NY", 300]]


class Names:
    def __init__(self, names):
        self.names = names

    async def resolve(self, word, field, values):
        if self.names.get(word) in values:
            return SimpleNamespace(status="resolved", candidate_id=values.index(self.names[word]))
        return SimpleNamespace(status="unmatched", candidate_id=None)


def _listing(question, columns=("A", "C")):
    summary, index = table_fixture([(1, 1, POLICIES)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_list", table_id=table.id, column_ids=list(columns),
                            identity_column_ids=["A"], statistic="all")
    return summary, index, without_fixed_groups(QuestionIntent(False, "row_list", (), True, plan), summary, question)


def test_a_list_asked_for_its_highest_or_lowest_number_becomes_its_top_row():
    assert _listing("보험가액이 가장 큰 계약은?")[2].tabular_query.model_dump(include={"order_by", "descending", "limit"}) \
        == {"order_by": "C", "descending": True, "limit": 1}
    assert _listing("보험가액이 제일 작은 계약은?")[2].tabular_query.descending is False
    assert _listing("계약 목록 보여줘")[2].tabular_query.order_by is None          # not asked
    assert _listing("laptop 목록 보여줘")[2].tabular_query.order_by is None        # "top" inside a word
    assert _listing("가장 큰 계약은?", columns=("A", "B"))[2].tabular_query.order_by is None  # no number to order


def test_korean_column_names_are_read_among_the_headers_and_stated():
    names = Names({"보험가액": "InsuredValue", "계약": "Policy"})
    for question, expected in (("보험가액이 가장 큰 계약은?", "P2"), ("보험가액이 제일 작은 계약은?", "P1")):
        summary, index, intent = _listing(question)
        answer = asyncio.run(translated_filter_answer(question, summary, index, intent, resolver=names))
        assert answer.answer.startswith("해석: ‘보험가액’ → InsuredValue") and f"Policy: {expected}" in answer.answer
    summary, index, intent = _listing("보험가액이 가장 큰 계약은?")
    assert asyncio.run(translated_filter_answer("보험가액이 가장 큰 계약은?", summary, index, intent,
                                                resolver=Names({}))) is None  # nothing read, nothing answered


def test_a_trend_the_series_route_cannot_bind_is_answered_by_the_insight_stating_it(monkeypatch):
    from app.agent.query import verified_series_answers as module
    good = {"title": "공기질이 '좋음'인 날의 비율 변화", "topic": "Good", "category": "change", "confidence": 1.0,
            "fact": "공기질이 '좋음'인 날의 비율: 1999년 34.1%에서 2023년 40.4%로 6.3%p 증가했습니다.",
            "support_references": ["data!b2", "data!b3"]}
    fair = {**good, "title": "공기질이 '보통'인 날의 비율 변화", "fact": good["fact"].replace("좋음", "보통")}
    summary, index = table_fixture([(1, 1, [["Year", "Good"], [1999, 34.1], [2023, 40.4]])], sheet_name="Data")
    monkeypatch.setattr(module, "build_verified_question_context", lambda _summary: {"insights": [good, fair]})
    answer = module.verified_series_answer("공기질 좋음 비율 추이 알려줘", summary, index)
    assert answer is not None and answer.answer == good["fact"] and len(answer.evidence) == 2
    assert module.verified_series_answer("공기질 비율 추이 알려줘", summary, index) is None  # 좋음·보통 tie
    assert module.verified_series_answer("미세먼지 추이 알려줘", summary, index) is None


def test_a_yes_no_column_the_question_names_is_read_as_yes_unless_negated():
    from app.agent.query.tabular_query_models import TabularFilter
    rows = [["Policy", "Earthquake", "Flood"], ["P1", "Y", "N"], ["P2", "N", "Y"], ["P3", "Y", "Y"]]
    summary, index = table_fixture([(1, 1, rows)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_count", table_id=table.id, column_ids=[], statistic="all",
                            filters=[TabularFilter(column_id="B", operator="equals", value="Y")])
    ask = lambda question: asyncio.run(translated_filter_answer(question, summary, index, QuestionIntent(
        False, "row_count", (), True, plan), resolver=Names({"지진": "Earthquake"})))
    answer = ask("지진 보험 가입 계약 수는?")
    assert answer.answer.startswith("해석: ‘지진’ → Earthquake = Y") and "2건" in answer.answer
    assert ask("지진 보험 미가입 계약 수는?") is None    # negated: the plan's Y is not what was asked
    assert ask("홍수 보험 가입 계약 수는?") is None      # names another column than the plan's


def test_a_word_naming_what_each_row_is_does_not_conflict_with_a_count():
    from app.agent.query.tabular_query_models import TabularFilter
    rows = [["Policy", "Construction", "InsuredValue"], ["P1", "Frame", 100], ["P2", "Masonry", 900], ["P3", "Frame", 300]]
    summary, index = table_fixture([(1, 1, rows)])
    table = build_query_tables(summary)[0]
    plan = TabularQueryPlan(operation="row_count", table_id=table.id, column_ids=[], statistic="all",
                            filters=[TabularFilter(column_id="B", operator="equals", value="Frame")])
    ask = lambda question, names: asyncio.run(translated_filter_answer(question, summary, index, QuestionIntent(
        False, "row_count", (), True, plan), resolver=Names(names)))
    # "계약" names Policy, one per row: the rows counted, not another column asked about.
    answer = ask("목조 건물 계약은 몇 건이야?", {"목조 건물": "Frame", "계약": "Policy"})
    assert answer.answer.startswith("해석: ‘목조 건물’ → Construction = Frame") and "2건" in answer.answer
    # A measured column the plan does not read still rejects the reading.
    assert ask("목조 건물 보험가액은 몇 건이야?", {"목조 건물": "Frame", "보험가액": "InsuredValue"}) is None
