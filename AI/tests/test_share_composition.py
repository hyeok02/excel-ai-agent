"""A total row and its own breakdown are a whole and its parts, not two peers."""
from app.services.insights.narratives.ranked_narratives import ranked_report
from tests.support.share_interpretation_fixtures import context

HEADERS = ("Group", "Shares Owned", "Percent Owned (%)")


def _facts(values):
    insights, _ = ranked_report(context(values, HEADERS))
    return [item for item in insights if "비중" in item.title]


def test_a_row_equal_to_the_sum_of_the_others_is_described_as_their_whole() -> None:
    items = _facts([("All Holders", 6580, 65.81), ("Holders - Managers", 5600, 56),
                    ("Holders - Banks", 300, 3), ("Holders - Pensions", 680, 6.81)])

    assert len(items) == 1
    fact = items[0].fact
    assert "All Holders의 비중은 65.81%" in fact and "Holders - Managers(56.00%)" in fact
    assert "85.1%를 차지" in fact and "%p 더 높습니다" not in fact


def test_a_group_named_inside_its_member_is_never_compared_as_a_peer() -> None:
    items = _facts([("All Holders", 7000, 70), ("Holders - Managers", 5600, 56), ("Other", 100, 1)])

    assert not any("%p 더 높습니다" in item.fact for item in items)


def test_peers_keep_their_gap_with_matching_decimals() -> None:
    items = _facts([("Region North", 6581, 65.81), ("Region South", 3400, 34)])

    assert "Region South의 비중은 34.00%" in items[0].fact and "31.81%p 더 높습니다" in items[0].fact


def test_top_holders_share_their_record_date_once_without_a_disclaimer() -> None:
    rows = [(rank, f"Holder {rank}", (10 - rank) * 10, 10 - rank, "2024-12-31T00:00:00") for rank in range(1, 4)]
    insights, _ = ranked_report(context(rows, ("Rank", "Name", "Quantity", "Share (%)", "Date")))
    fact = next(item.fact for item in insights if "개 항목의 비중 합계" in item.title)

    assert "2024년 12월 31일 기준 상위 3개 항목의 비중 합계는 24%" in fact
    assert "지배력" not in fact and "원본 순위" not in fact
