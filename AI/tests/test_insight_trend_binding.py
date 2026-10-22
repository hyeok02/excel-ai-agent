"""Directions and dated endpoints cannot be borrowed across cited metrics."""
import pytest

from tests.test_insight_relation_grounding import context, verify


def source():
    result = context([], records=[{
        "location": f"Sheet1!A{row}:C{row}", "values": [
            {"cell": f"A{row}", "value": period},
            {"cell": f"B{row}", "label": "매출", "value": revenue},
            {"cell": f"C{row}", "label": "비용", "value": cost},
        ],
    } for row, period, revenue, cost in ((2, "2024-01-01", 100, 50),
                                        (3, "2024-02-01", 80, 60))])
    result["sheets"][0]["business_facts"]["numeric_changes"] = [{
        "metric": metric, "earliest_period": "2024-01-01", "latest_period": "2024-02-01",
        "earliest_value": old, "latest_value": new, "change": new - old,
        "change_rate_percent": (new - old) / old * 100, "evidence": ["Sheet1!A2:C3"],
    } for metric, old, new in (("매출", 100, 80), ("비용", 50, 60))]
    return result


@pytest.mark.parametrize(("fact", "valid"), [
    ("매출은 증가했습니다.", False), ("비용은 감소했습니다.", False),
    ("매출은 감소했습니다.", True), ("비용은 증가했습니다.", True),
    ("매출은 감소했고 비용은 증가했습니다.", True),
    ("매출은 증가했고 비용은 감소했습니다.", False),
    ("매출은 100에서 80으로 감소했습니다.", True),
    ("비용은 100에서 80으로 감소했습니다.", False),
    ("매출은 2024년 1월 100에서 2024년 2월 80으로 감소했습니다.", True),
    ("매출은 2024년 2월 100에서 2024년 1월 80으로 감소했습니다.", False),
])
def test_metric_and_period_binding(fact, valid):
    result = verify(fact, source())
    assert (result.validation.blocked_count == 0) is valid
    assert any(item.fact == fact for item in result.insights) is valid


def test_a_single_different_metric_cannot_supply_change_evidence():
    data = source()
    data["sheets"][0]["business_facts"]["numeric_changes"] = [
        data["sheets"][0]["business_facts"]["numeric_changes"][0],
    ]
    assert verify("비용은 감소했습니다.", data).validation.blocked_count == 1


@pytest.mark.parametrize("fact", ["매출은 증가했습니다.", "매출은 감소했습니다.", "매출은 가장 큽니다."])
def test_one_point_never_establishes_direction_or_ranking(fact):
    result = verify(fact, context([("A2", "매출"), ("B2", 100)]))
    assert result.validation.blocked_count == 1
