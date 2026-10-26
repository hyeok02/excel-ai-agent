from copy import deepcopy

import pytest

from app.agent.query.verified_insight_answers import validated_verified_insight_answer
from tests.test_verified_insight_answers import _execution


def _cards():
    execution = _execution()
    values = {"A1": "Alpha Capital", "A2": 60, "B1": "Beta Assets", "B2": 40}
    result = execution.steps[0].result
    result.evidence = [item for item in result.evidence if item.reference in values]
    for item in result.evidence:
        item.value = values[item.reference]
    items = [
        {"title": "Alpha Capital·Beta Assets 비중 차이", "category": "metric",
         "fact": "Alpha Capital은 Beta Assets보다 20%p 높습니다.",
         "support_references": ["인원!A1:A2", "인원!B1:B2"]},
        {"title": "Alpha Capital", "category": "metric",
         "fact": "Alpha Capital의 비중은 60%입니다.",
         "support_references": ["인원!A1:A2"]},
    ]
    execution.steps[0].result.data["verified_insights"] = items
    return execution, items


@pytest.mark.parametrize("order", [False, True])
def test_exact_card_question_beats_an_overlapping_comparison_card(order):
    execution, items = _cards()
    if order:
        items.reverse()
    answer = validated_verified_insight_answer(
        "Alpha Capital 관련 수치와 원본 근거를 보여줘", execution, False,
    )
    assert answer is not None and answer.answer == "Alpha Capital의 비중은 60%입니다."
    assert answer.verification.level == "source_checked"
    assert {item.reference for item in answer.evidence} == {"A1", "A2"}


def test_exact_comparison_title_still_selects_its_complete_fact():
    execution, items = _cards()
    answer = validated_verified_insight_answer(
        items[0]["title"] + " 관련 수치와 원본 근거를 보여줘", execution, False,
    )
    assert answer is not None and answer.answer == items[0]["fact"]


def test_missing_exact_card_evidence_does_not_switch_to_another_card():
    execution, items = _cards()
    items[1]["support_references"] = ["인원!Z99"]
    assert validated_verified_insight_answer(
        "Alpha Capital 관련 수치와 원본 근거를 보여줘", execution, False,
    ) is None


def test_duplicate_exact_titles_are_not_arbitrarily_selected():
    execution, items = _cards()
    duplicate = deepcopy(items[1])
    duplicate["fact"] = "Alpha Capital의 비중은 50%입니다."
    items.append(duplicate)
    assert validated_verified_insight_answer(
        "Alpha Capital 관련 수치와 원본 근거를 보여줘", execution, False,
    ) is None


@pytest.mark.parametrize("question", [
    "2024년 Alpha Capital 관련 수치와 원본 근거를 보여줘",
    "서울 Alpha Capital 관련 수치와 원본 근거를 보여줘",
    "Alpha Capital 평균을 알려줘",
    "Gamma Capital 관련 수치와 원본 근거를 보여줘",
])
def test_extra_conditions_are_not_erased_to_force_a_title_match(question):
    execution, _ = _cards()
    assert validated_verified_insight_answer(question, execution, False) is None
