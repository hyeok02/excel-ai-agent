from app.services.insights.models import WorkbookInsight
from app.services.insights.verification.topic_grounding import grounded_topic


def _canonical(topic):
    return WorkbookInsight(
        title=f"{topic} 변화", topic=topic, fact="원본에서 확인했습니다.",
        category="change", severity="info", evidence=["Data!A1"], confidence=1,
    )


def test_cited_canonical_translation_is_kept():
    assert grounded_topic(
        "전체 직원 수", ["Total Employees"], {"data!a1"},
        [_canonical("전체 직원 수")],
    )


def test_unrelated_source_words_cannot_be_combined_into_a_topic():
    assert not grounded_topic(
        "매출 직원 수", ["매출", "직원 수"], {"data!a1"},
    )


def test_literal_cited_label_can_be_a_topic_without_a_canonical_report():
    assert grounded_topic("설비 가동률", ["설비 가동률", "91.5%"], {"data!a1"})


def test_date_or_uncited_canonical_topic_is_not_displayed():
    assert not grounded_topic("2025-01-01", ["2025-01-01"], {"data!a1"})
    assert not grounded_topic(
        "전체 직원 수", ["Total Employees"], {"data!b1"},
        [_canonical("전체 직원 수")],
    )
