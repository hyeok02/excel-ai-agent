from app.agent.query.ambiguity_answers import ambiguous_source_answer
from app.agent.query.ambiguity_metrics import metric_candidates
from app.agent.query.metric_observation_answers import metric_observation_answer
from app.agent.query.metric_scalar_answers import metric_scalar_answer
from tests.test_metric_observation_answers import _index, _report


def test_same_date_different_reporting_periods_show_named_actual_candidates():
    index = _index({"Results": _report()})
    result = ambiguous_source_answer("2024년 9월 30일 Operating Income은?", None, index)
    assert result.status == "insufficient_evidence"
    assert result.verification.level == "unverified"
    assert "회계연도" in result.answer and "분기" in result.answer
    assert "'Results'!E9" in result.answer and "'Results'!F9" in result.answer


def test_suggested_exact_cell_period_followups_actually_resolve_the_ambiguity():
    index = _index({"Results": _report()})
    candidates = metric_candidates("2024년 9월 30일 Operating Income은?", index)
    assert len(candidates) == 2
    for candidate in candidates:
        assert ambiguous_source_answer(candidate.followup, None, index) is None
        result = metric_observation_answer(candidate.followup, None, index)
        assert result is not None and result.status == "answered"
        assert result.verification.level == "request_checked"
        expected = "650" if "E9" in candidate.scope else "180"
        assert expected in result.answer


def test_clear_period_comparisons_and_explicit_grains_are_not_blocked():
    index = _index({"Results": _report()})
    for question in [
        "Operating Income은 2023년에서 2024년으로 얼마나 증가했어?",
        "2024년 9월 30일 종료 회계연도 Operating Income과 같은 날짜 종료 분기를 구분해줘.",
        "2024년 9월 30일 분기 Operating Income은?",
        "Operating Income의 시작 값과 마지막 값을 비교해줘",
    ]:
        assert ambiguous_source_answer(question, None, index) is None


def test_missing_period_prompts_for_existing_source_dates():
    result = ambiguous_source_answer("Operating Income은?", None, _index({"Results": _report()}))
    assert result is not None
    assert "2022년 9월 30일" in result.answer and "2024년 9월 30일" in result.answer


def test_conflicting_scalar_units_have_usable_distinct_sheet_choices():
    index = _index({
        "Ledger USD": {"A1": "Amounts in USD millions", "A3": "Revenue", "B3": 100},
        "Ledger EUR": {"A1": "Amounts in EUR millions", "A3": "Revenue", "B3": 100},
    })
    result = ambiguous_source_answer("Revenue는 얼마야?", None, index)
    assert "미국 달러" in result.answer and "유로" in result.answer
    candidates = metric_candidates("Revenue는 얼마야?", index)
    for candidate in candidates:
        assert ambiguous_source_answer(candidate.followup, None, index) is None
        answer = metric_scalar_answer(candidate.followup, None, index)
        assert answer is not None and answer.status == "answered"
        assert answer.verification.level == "request_checked"


def test_unknown_or_contradictory_cell_address_cannot_be_consumed_as_valid_scope():
    index = _index({"Results": _report()})
    for question in ["'Missing'!E9의 Operating Income은 2024년에 얼마야?",
                     "'Results'!Z999의 Operating Income은 2024년에 얼마야?",
                     "'Results'!E9와 'Results'!Z999의 Operating Income은 2024년에 얼마야?"]:
        result = metric_observation_answer(question, None, index)
        assert result is None or result.verification.level != "request_checked"


def test_latest_cannot_silently_choose_the_company_with_the_newest_report():
    index = _index({
        "First report": {"A1": "Alpha Company", "A3": "Period", "B3": "2024-12-31",
                         "C3": "2025-12-31", "A5": "Revenue", "B5": 80, "C5": 100},
        "Second report": {"A1": "Beta Company", "A3": "Period", "B3": "2025-12-31",
                          "C3": "2026-12-31", "A5": "Revenue", "B5": 200, "C5": 300},
    })
    result = ambiguous_source_answer("최신 Revenue는?", None, index)
    assert result is not None and "First report" in result.answer and "Second report" in result.answer
    assert ambiguous_source_answer("Alpha Company의 최신 Revenue는?", None, index) is None


def test_undated_question_prefers_unique_exact_snapshot_over_history_or_semantic_aliases():
    index = _index({"Report": {
        "A1": "Example Company", "A2": "Amounts in USD millions",
        "A4": "Total Debt", "B4": 75,
        "A8": "Period", "B8": "2024-12-31", "C8": "2025-12-31",
        "A9": "Total Debt", "B9": 30, "C9": 50,
        "A10": "Total Liabilities", "B10": 200, "C10": 300,
    }})
    question = "Example Company의 총부채(Total Debt)는 얼마야? 단위도 알려줘."
    assert ambiguous_source_answer(question, None, index) is None
    answer = metric_scalar_answer(question, None, index)
    assert answer is not None and "75" in answer.answer
    assert answer.verification.level == "request_checked"


def test_exact_dated_metric_label_excludes_other_semantic_aliases():
    index = _index({"Report": {
        "A1": "Amounts in USD millions", "B2": "Annual actual",
        "A3": "Period", "B3": "2024-12-31", "C3": "2025-12-31",
        "A4": "Total Debt", "B4": 20, "C4": 30,
        "A5": "Total Liabilities", "B5": 200, "C5": 300,
    }})
    assert ambiguous_source_answer("2025년 총부채(Total Debt)는?", None, index) is None


def test_snapshot_preference_never_hides_multiple_conflicting_snapshots():
    index = _index({"Report": {
        "A1": "Amounts in USD millions", "A3": "Total Debt", "B3": 20,
        "A5": "Total Debt", "B5": 30,
        "A8": "Period", "B8": "2024-12-31", "C8": "2025-12-31",
        "A9": "Total Debt", "B9": 40, "C9": 50,
    }})
    answer = ambiguous_source_answer("총부채(Total Debt)는?", None, index)
    assert answer is not None and "A9" not in answer.answer
    assert "B3" in answer.answer and "B5" in answer.answer
