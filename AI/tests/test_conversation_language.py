"""Question grammar is flexible; semantic restrictions stay exact."""
import pytest

from app.agent.query.conversation_checks import resolution_is_safe
from app.agent.query.conversation_models import ContextResolutionDraft
from app.agent.query.conversation_periods import bound_relative_question


def entries():
    return [{"id": "turn:0", "hint": {"question": "2026년 1월 31일 종료 연간/분기 순이익은?"},
             "source_cells": [
                 {"reference": "Summary!A1", "value": "Net Income"},
                 {"reference": "Summary!B1", "value": "2026-01-31T00:00:00"},
                 {"reference": "Summary!C1", "value": "Quarter Ended"},
                 {"reference": "Summary!B2", "value": 100},
             ]}]


def safe(original, rewritten, context=None):
    draft = ContextResolutionDraft(status="resolved", question=rewritten, context_ids=["turn:0"])
    return resolution_is_safe(original, draft, context or entries())


@pytest.mark.parametrize("original,rewritten", [
    ("Nation-A의 직원 수는 몇 명이야?", "Summary 시트에서 Nation-A의 직원 수를 알려줘"),
    ("그중 평균은?", "Summary 시트의 average를 알려줘"),
    ("그럼 2027년 예상 매출은?", "Summary 시트에서 2027년 예상 매출을 알려줘"),
    ("그럼 일본은?", "Summary 시트에서 일본(Japan)의 Total Employees는?"),
    ("그중 변경점이 신규인 장비만 보여줘", "Summary 시트에서 상태가 'x'인 장비 중 변경점이 '신규'인 장비만 보여줘"),
])
def test_question_grammar_and_explicit_alias_additions_are_allowed(original, rewritten):
    assert safe(original, rewritten)


@pytest.mark.parametrize("original,rewritten", [
    ("그중 #42 값은?", "Summary의 #420 값은?"),
    ("그중 3 미만은?", "Summary에서 3 초과는?"),
    ("그중 20% 이상은?", "Summary에서 20 이상은?"),
    ("그중 제외한 평균은?", "Summary의 평균은?"),
    ("그럼 2027년 예상 매출은?", "Summary의 2026년 예상 매출은?"),
    ("그럼 2027년 실제 매출은?", "Summary의 2027년 예상 매출은?"),
    ("그럼 일본은?", "Summary의 중국(China)의 Total Employees는?"),
    ("그중 천 달러 합계는?", "Summary의 백만 달러 합계는?"),
    ("그중 East 값은?", "Summary의 Northeast 값은?"),
    ("그중 US 값은?", "Summary의 AUS 값은?"),
    ("그중 변경점이 신규인 장비만 보여줘", "Summary 시트에서 변경점이 '기존'인 장비만 보여줘"),
])
def test_semantic_constraints_remain_mandatory(original, rewritten):
    assert not safe(original, rewritten)


def test_previous_year_same_quarter_is_bound_to_a_corroborated_date():
    original = "그럼 전년도 같은 분기 순이익은?"
    rewritten = "Summary 시트에서 2025년 1월 31일 종료 분기 순이익은?"
    assert "2025년 1월 31일" in bound_relative_question(original, entries())
    assert safe(original, rewritten)
    assert not safe(original, rewritten.replace("2025", "2024"))
    assert not safe(original, rewritten.replace("분기", "회계연도"))


def test_relative_period_without_one_source_backed_prior_date_is_not_guessed():
    original = "그럼 전년도 같은 분기 순이익은?"
    context = entries()
    context[0]["hint"]["question"] = "2024년 1월 31일 종료 분기 순이익은?"
    assert bound_relative_question(original, context) is None
    assert not safe(original, "Summary 시트의 2023년 1월 31일 분기 순이익은?", context)
