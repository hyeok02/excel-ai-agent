from app.agent.query.verified_insight_constraints import insight_intent_matches
from app.agent.query.verified_insight_matching import verified_insight_score


def _item(topic: str, fact: str, category: str = "change") -> dict:
    return {"title": topic, "topic": topic, "category": category, "fact": fact}


def test_classifier_target_cannot_override_an_explicit_unknown_team() -> None:
    item = _item(
        "Total Employees",
        "전체 직원 수는 3,955명에서 5,417명으로 증가했습니다.",
    )

    assert verified_insight_score(
        "IT 직원 수 변화", "IT 직원 수 변화 Total Employees", item
    ) == 0


def test_every_explicit_identity_must_match_the_fact() -> None:
    item = _item(
        "Supplier Beta Output",
        "Supplier Beta의 Output은 13,500입니다.",
        "summary",
    )

    assert verified_insight_score(
        "Supplier Alpha Output", "Supplier Alpha Output", item
    ) == 0


def test_classifier_kind_alone_cannot_turn_a_snapshot_into_a_change() -> None:
    item = _item(
        "전체 직원 수 변화",
        "전체 직원 수는 3,955명에서 5,417명으로 증가했습니다.",
    )

    assert not insight_intent_matches("현재 전체 직원 수는?", item, "comparison")


def test_semantic_alias_still_matches_across_languages() -> None:
    item = _item(
        "Revenue change", "Revenue increased from 100 to 120."
    )

    assert verified_insight_score("매출 변화", "매출 변화", item) > 0
