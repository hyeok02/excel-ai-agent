from app.services.insights.facts.source_records import source_record_insights
from app.services.insights.quality import _change_insight
from app.services.insights.verification.validation_index import workbook_evidence_index
from app.services.insights.verification.validator import _validate_insight


def _context(*rows):
    return {"sheets": [{"name": "원본", "business_facts": {
        "selected_records": [{"values": [
            {"cell": cell, "value": value} for cell, value in row
        ]} for row in rows],
    }}]}


def _change(metric):
    return {
        "metric": metric,
        "earliest_period": "2025-01-01",
        "earliest_value": 10,
        "latest_period": "2025-06-01",
        "latest_value": 8,
        "change": -2,
        "change_rate_percent": -20,
        "evidence": ["'원본'!A1", "'원본'!B1"],
    }


def test_change_topics_follow_source_metric_across_domains():
    for metric in ("월간 불량률", "총 거래액", "Total Employees"):
        item = _change_insight(None, _change(metric))
        assert item.topic == metric
        assert item.category == "change"


def test_change_topic_is_absent_for_identifier_or_date():
    for metric in ("SP_METRIC_01", "2025-01-01", "12345"):
        assert _change_insight(None, _change(metric)).topic is None


def test_record_topic_comes_from_a_cited_label_cell():
    context = _context(
        (("A2", "설비 가동률"), ("B2", 91.5)),
        (("A3", "쇠고기(종류)/가공품"), ("B3", "국내산(한우)")),
    )

    items = source_record_insights(context, 2)

    assert {item.topic for item in items} == {"설비 가동률", "쇠고기(종류)/가공품"}
    for item in items:
        assert "'원본'!" in " ".join(item.evidence)

    validated = _validate_insight(items[0], workbook_evidence_index(context))
    assert validated is not None
    assert validated.topic == items[0].topic


def test_record_topic_is_absent_when_display_title_is_not_a_cited_label():
    context = _context((("A2", "2025-01-01"),
                        ("B2", "장문의 사건 설명 " * 8),
                        ("C2", "추가적인 사건 설명 " * 8)))

    item = source_record_insights(context, 1)[0]

    assert item.title == "원본에서 확인한 내용"
    assert item.topic is None
