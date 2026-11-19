"""Two years' change, or the highest year, of a named annual series."""
from types import SimpleNamespace

from app.agent.query import series_period_answers as module
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Period", "Coal", "Gas"], ["Annual Totals", None, None], [2020, 773, 1600], [2021, 900, 1580], [2022, 830, 1690]]


class Names:
    async def resolve(self, word, field, values):
        named = {"석탄": "Coal", "가스": "Gas"}.get(word)
        return SimpleNamespace(status="resolved", candidate_id=values.index(named)) if named in values else \
            SimpleNamespace(status="unmatched", candidate_id=None)


def _ask(question):
    summary, index = table_fixture([(1, 1, ROWS)], sheet_name="Generation")
    return module.series_period_answer(question, summary, index, Names())


def test_two_years_change_and_the_highest_year_are_read_from_the_annual_rows():
    change = _ask("2020년 대비 2022년 석탄 변화는?")
    assert change is not None and "2020년 773 → 2022년 830, 57(7.37%) 증가했습니다." in change.answer
    assert "가장 높았던 해는 2021년 900" in _ask("석탄이 가장 많았던 해는?").answer
    assert "가장 낮았던 해는 2021년 1,580" in _ask("가스가 가장 적었던 해는?").answer


def test_a_year_the_series_lacks_or_an_unnamed_series_answers_nothing():
    assert _ask("2019년 대비 2022년 석탄 변화는?") is None
    assert _ask("2020년 대비 2022년 풍력 변화는?") is None


def test_one_years_series_are_compared_when_no_single_series_is_named():
    answer = _ask("2021년 가장 많은 에너지원은?")
    assert answer is not None and "2021년 값 중 가장 높은 항목은 Gas 1,580" in answer.answer
    assert _ask("2021년 석탄이 가장 많은 달은?") is None  # one series named: not a comparison across series


def test_the_last_n_years_are_averaged():
    answer = _ask("최근 2년 석탄 평균은?")
    assert answer is not None and "최근 2년(2021년 900, 2022년 830) 평균은 865.0" in answer.answer
