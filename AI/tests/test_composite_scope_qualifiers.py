"""Source qualifiers remain attached; genuine subsequent requests still split."""
import pytest
from types import SimpleNamespace

from app.agent.query.composite_split import split_compound_question


@pytest.mark.parametrize("question", [
    "부산의 공립 유치원수는 몇 개야? (2023년 유치원 현황 시트 기준)",
    "Revenues 값은? (Forecast 범위 기준)",
    "Revenue value? (in sheet Forecast)",
])
def test_parenthetical_source_scope_is_not_a_second_question(question):
    assert split_compound_question(question) is None


def test_a_real_second_question_keeps_first_source_qualifier_verbatim():
    question = "매출은? (Actual 시트 기준) 비용은? (Forecast 시트 기준)"
    split = split_compound_question(question)
    assert split.parts == ("매출은? (Actual 시트 기준)", "비용은? (Forecast 시트 기준)")


def test_parenthetical_question_is_not_a_scope_qualifier():
    split = split_compound_question("매출은? (비용도 알려줘?)")
    assert split.parts == ("매출은?", "(비용도 알려줘?)")


def test_distinct_sheet_scopes_are_not_discarded_when_split():
    split = split_compound_question("A 표: 매출은? (Q1 시트 기준) 고객 수는?")
    assert split.shared_prefix == "A 표"
    assert split.parts == ("매출은? (Q1 시트 기준)", "고객 수는?")


def source_sheets(*names):
    return SimpleNamespace(summary=SimpleNamespace(sheets=[SimpleNamespace(name=name) for name in names]))


@pytest.mark.parametrize("suffix", [
    "(2023년 유치원 현황)", "('2023년 유치원 현황')", '("2023년 유치원 현황")',
    "(2023년 유치원 현황).", "(2023년 유치원 현황)?",
])
def test_bare_original_sheet_suffix_is_not_a_second_task(suffix):
    question = "부산의 공립 유치원수는 몇 개야? " + suffix
    assert split_compound_question(question, source_sheets("2023년 유치원 현황")) is None


@pytest.mark.parametrize("sheet", ["Forward plan", "Revenue (v2)", "Balance = 0", "2025년 지역표"])
def test_scope_recognition_uses_source_names_not_a_particular_workbook(sheet):
    question = f"값은 얼마야? ({sheet})"
    assert split_compound_question(question, source_sheets(sheet)) is None


def test_bare_qualifier_remains_with_its_question_before_a_real_second_task():
    question = "매출은? (Actual) 비용은? (Forecast)"
    split = split_compound_question(question, source_sheets("Actual", "Forecast"))
    assert split.parts == ("매출은? (Actual)", "비용은? (Forecast)")


def test_unknown_parenthetical_action_still_forms_a_second_question():
    question = "매출은? (비용도 알려줘)"
    split = split_compound_question(question, source_sheets("Actual"))
    assert split.parts == ("매출은?", "(비용도 알려줘)")


def test_index_sheet_names_are_a_safe_fallback_without_a_summary():
    sources = SimpleNamespace(index=SimpleNamespace(rows=[SimpleNamespace(sheet_name="Facts", cells=())]))
    assert split_compound_question("수량은? (Facts)", sources) is None
