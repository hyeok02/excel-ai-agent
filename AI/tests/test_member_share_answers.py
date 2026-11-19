"""One named member's share of a column's total."""
from types import SimpleNamespace

from app.agent.query.member_share_answers import member_share_answer
from tests.tabular_query_fixtures import table_fixture

ROWS = [["Category", "TotalPrice"], ["Bars", 30], ["Cookies", 50], ["Bars", 20]]


class Names:
    async def resolve(self, word, field, values):
        return (SimpleNamespace(status="resolved", candidate_id=values.index("TotalPrice"))
                if word == "판매금액" and "TotalPrice" in values else SimpleNamespace(status="unmatched", candidate_id=None))


def test_a_named_members_share_of_the_measure_total_is_computed():
    summary, index = table_fixture([(1, 1, ROWS)], sheet_name="Sales")
    answer = member_share_answer("Bars가 전체 판매금액에서 차지하는 비중은?", summary, index, Names())
    assert answer.answer.endswith("Category = Bars의 TotalPrice 합계 50는 전체 100의 50.00%입니다.")
    assert answer.answer.startswith("해석: ‘판매금액’ → TotalPrice")
    assert member_share_answer("Bars 판매금액 합계는?", summary, index, Names()) is None  # no share asked
    assert member_share_answer("Chips가 전체 판매금액에서 차지하는 비중은?", summary, index, Names()) is None
