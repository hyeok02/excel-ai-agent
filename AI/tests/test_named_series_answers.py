"""A trend question naming a series no report card shows reads the name among every series."""
from types import SimpleNamespace

from app.agent.query import verified_series_answers as module
from tests.tabular_query_fixtures import table_fixture


class Names:
    def __init__(self, names):
        self.names = names

    async def resolve(self, word, field, values):
        if self.names.get(word) in values:
            return SimpleNamespace(status="resolved", candidate_id=values.index(self.names[word]))
        return SimpleNamespace(status="unmatched", candidate_id=None)


def _fact(topic, section, fact, priority):
    return priority, SimpleNamespace(topic=topic, fact=fact, title=f"{topic} 변화 · {section}", category="change",
                                     evidence=["'Data'!B2", "'Data'!B3"],
                                     model_dump=lambda: {"category": "change", "fact": fact, "title": topic, "topic": topic})


def _ask(monkeypatch, question, facts, names):
    summary, index = table_fixture([(1, 1, [["Year", "Coal"], [2016, 10], [2025, 7]])], sheet_name="Data")
    monkeypatch.setattr(module, "build_workbook_context", lambda _summary: {})
    monkeypatch.setattr(module, "all_series_facts", lambda _context: facts)
    return module.named_series_answer(question, summary, index, resolver=Names(names))


ANNUAL = _fact("Coal", "연간 합계", "연간 합계의 Coal: 2016년 10에서 2025년 7로 3(30.00%) 감소했습니다.\n"
               "가장 낮았던 시점은 2025년 7입니다.", 0)
MONTHLY = _fact("Coal", "2026년", "2026년의 Coal: 2026년 1월 1에서 2026년 8월 2로 증가했습니다.\n"
                "가장 높았던 시점은 2026년 7월 3입니다.", 2)


def test_the_named_series_is_answered_from_its_annual_section_with_the_reading_stated(monkeypatch):
    answer = _ask(monkeypatch, "석탄 발전량 추이 알려줘", [MONTHLY, ANNUAL], {"석탄": "Coal"})
    assert answer.answer.startswith("해석: ‘석탄’ → Coal\n연간 합계의 Coal: 2016년 10")
    lowest = _ask(monkeypatch, "석탄 발전량이 가장 낮은 해는?", [MONTHLY, ANNUAL], {"석탄": "Coal"})
    assert lowest.answer.endswith("Coal: 가장 낮았던 시점은 2025년 7입니다.")


def test_another_section_never_answers_what_the_annual_series_does_not_state(monkeypatch):
    assert _ask(monkeypatch, "석탄 발전량이 가장 높은 해는?", [MONTHLY, ANNUAL], {"석탄": "Coal"}) is None
    assert _ask(monkeypatch, "석탄 발전량 추이 알려줘", [MONTHLY, ANNUAL], {}) is None  # nothing named
    twin = _fact("Coal", "연간 합계", ANNUAL[1].fact.replace("10", "11"), 0)
    assert _ask(monkeypatch, "석탄 발전량 추이 알려줘", [ANNUAL, twin], {"석탄": "Coal"}) is None  # two readings


def test_a_wider_word_inside_the_phrase_naming_a_series_does_not_compete_with_it(monkeypatch):
    total = _fact("Total", "연간 합계", "연간 합계의 Total: 2016년 20에서 2025년 25로 5(25.00%) 증가했습니다.", 0)
    names = {"석탄": "Coal", "석탄 발전량": "Coal", "발전량": "Total"}
    assert _ask(monkeypatch, "석탄 발전량 추이 알려줘", [total, ANNUAL], names).answer.startswith("해석: ‘석탄’ → Coal")
    assert _ask(monkeypatch, "발전량 추이 알려줘", [total, ANNUAL], names).answer.startswith("해석: ‘발전량’ → Total")


def test_the_head_word_of_a_phrase_is_what_its_first_word_specifies(monkeypatch):
    total = _fact("Total", "연간 합계", "연간 합계의 Total: 2016년 20에서 2025년 25로 5(25.00%) 증가했습니다.", 0)
    solar = _fact("Solar", "연간 합계", ANNUAL[1].fact.replace("Coal", "Solar"), 0)
    # "태양광 발전량" as a whole fits several solar series; 발전량 is still what 태양광 specifies.
    answer = _ask(monkeypatch, "태양광 발전량 추이 알려줘", [total, solar], {"태양광": "Solar", "발전량": "Total"})
    assert answer.answer.startswith("해석: ‘태양광’ → Solar")
    assert _ask(monkeypatch, "발전량 추이 알려줘", [total, solar], {"발전량": "Total"}).answer.startswith("해석: ‘발전량’ → Total")


def test_a_specifier_naming_no_series_is_said_instead_of_answering_the_total(monkeypatch):
    total = _fact("Total", "연간 합계", "연간 합계의 Total: 2016년 20에서 2025년 25로 5(25.00%) 증가했습니다.", 0)
    answer = _ask(monkeypatch, "풍력 발전량 추이 알려줘", [total, ANNUAL], {"발전량": "Total"})
    assert answer.status == "insufficient_evidence" and answer.answer.startswith("‘풍력’에 해당하는 계열을 원본에서 찾지 못했습니다")
    assert _ask(monkeypatch, "연간 발전량 추이 알려줘", [total, ANNUAL], {"발전량": "Total"}).status == "limited"
