"""수치가 같은 항목이 둘일 때도 같은 결과가 나오는지 검증한다."""
from app.services.insights.facts.fact_trends import numeric_changes


def _records():
    """두 열이 완전히 같은 값을 갖는 표. 정렬만으로는 승자가 갈리지 않는다."""
    return [
        {"location": "Sheet1!A1:C1", "values": [
            {"value": "2024-01-01"},
            {"value": 337, "label": "Operations"},
            {"value": 337, "label": "Human Resources"},
        ]},
        {"location": "Sheet1!A2:C2", "values": [
            {"value": "2025-01-01"},
            {"value": 437, "label": "Operations"},
            {"value": 437, "label": "Human Resources"},
        ]},
    ]


def test_picks_the_same_metric_every_time() -> None:
    orders = {tuple(item["metric"] for item in numeric_changes(_records()))
              for _ in range(20)}

    assert len(orders) == 1


def test_breaks_a_tie_by_name_so_the_report_reads_the_same_tomorrow() -> None:
    metrics = [item["metric"] for item in numeric_changes(_records())]

    assert metrics == sorted(metrics)
