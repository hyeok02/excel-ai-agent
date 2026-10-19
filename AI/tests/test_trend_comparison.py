"""Explicit multiple metrics compare aligned full trajectories without model calls."""
from dataclasses import replace

import pytest

from app.agent.query.trend_comparison import comparison_answer, comparison_candidates, comparison_missing_metrics
from app.agent.query.trend_selection import prepare_trend_candidate
from app.agent.query.trend_sources import trend_candidates
from tests.support.large_workbook_fixtures import offline
from tests.tabular_query_fixtures import table_fixture

QUESTION = "Permanent Employees와 Temporary Employees의 기간별 추이를 비교해줘"


def _source():
    return table_fixture([(1, 1, [["Date", "Permanent Employees", "Temporary Employees", "Revenue"],
        ["2024-01-01", 100, 20, 9000], ["2024-02-01", 130, 50, 8000],
        ["2024-03-01", 110, 40, 7000], ["2024-04-01", 120, 45, 6000]])])


def _prepared(summary, index, question=QUESTION):
    candidates = comparison_candidates(question, trend_candidates(summary, index, question))
    return [prepare_trend_candidate(candidate, index.rows) for candidate in candidates if not candidate.error]


def _answer(summary, index, prepared=None, question=QUESTION):
    return comparison_answer(question, prepared or _prepared(summary, index, question), list(index.rows),
                             set(), summary, index)


def test_aligned_metrics_show_each_rebound_and_exact_gap():
    summary, index = _source()
    answer = _answer(summary, index)
    assert answer.status == "answered" and answer.verification.level == "request_checked"
    assert answer.answer.count("하락 뒤 반등") == 2
    assert "마지막 관측값 차이(Permanent Employees - Temporary Employees), 2024-04-01: +75명" in answer.answer
    assert "전체 기간 증감의 차이(Permanent Employees - Temporary Employees), 2024-01-01 → 2024-04-01: -5명" in answer.answer
    assert "Revenue" not in answer.answer
    evidence = {item.reference for item in answer.evidence}
    assert {"A2", "A3", "A4", "A5", "B2", "B3", "B4", "B5", "C2", "C3", "C4", "C5"} <= evidence


@pytest.mark.parametrize("change", ["date", "unit", "entity", "relative_note", "grain"])
def test_incompatible_axes_units_or_scope_only_show_limited_individual_series(change):
    summary, index = _source()
    prepared = _prepared(summary, index)
    candidate, units = prepared[1]
    if change == "date":
        candidate = replace(candidate, observations=candidate.observations[:-1])
        units = units[:-1]
    elif change == "unit":
        units = tuple(replace(unit, identity=("USD",), suffix="USD") for unit in units)
    elif change == "entity":
        candidate = replace(candidate, table_id="Other!A1:C5")
    elif change == "relative_note":
        candidate = replace(candidate, period_note="기준일이 다른 상대기간")
    elif change == "grain":
        candidate = replace(candidate, observations=tuple(replace(point, grain="quarter") for point in candidate.observations))
    answer = _answer(summary, index, [prepared[0], (candidate, units)])
    if change == "relative_note":
        assert answer.status == "insufficient_evidence"  # Contradictory retained date metadata.
        return
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert "마지막 관측값 차이" not in answer.answer


def test_duplicate_source_for_one_metric_keeps_clarification_path():
    summary, index = _source()
    prepared = _prepared(summary, index)
    candidate, units = prepared[0]
    prepared.append((replace(candidate, table_id="Other!A1:B5"), units))
    assert _answer(summary, index, prepared) is None


def test_single_metric_alias_does_not_become_a_multi_metric_request():
    summary, index = _source()
    assert _answer(summary, index, question="Permanent Employees 추이를 설명해줘") is None


@pytest.mark.parametrize("question", [
    QUESTION + " 그리고 UnknownMetric도", QUESTION + " 평균도",
    "Permanent Employees 또는 Temporary Employees의 추이를 비교해줘",
])
def test_missing_metric_extra_operation_or_alternative_request_not_certified(question):
    summary, index = _source()
    answer = _answer(summary, index, question=question)
    assert answer is None or answer.verification.level != "request_checked"


def test_generic_total_headcount_is_not_an_extra_named_department_metric():
    summary, index = table_fixture([(1, 1, [["Date", "Total Employees", "Services", "Engineering"],
        ["2024-01-01", 100, 20, 30], ["2024-02-01", 120, 30, 40]])])
    question = "Services와 Engineering 인원의 추이를 비교해줘"
    candidates = trend_candidates(summary, index, question)
    assert len(candidates) == 3
    selected = comparison_candidates(question, candidates)
    assert {candidate.observations[0].label.value for candidate in selected} == {"Services", "Engineering"}


def test_error_and_unknown_label_candidates_are_not_lost_during_selection():
    summary, index = _source()
    candidates = trend_candidates(summary, index, QUESTION)
    broken = replace(candidates[0], observations=(), context=(candidates[0].observations[0].label,), error="missing_or_invalid_value")
    unknown = replace(candidates[0], observations=(), context=(), error="incomplete_source")
    selected = comparison_candidates(QUESTION, [broken, candidates[1], unknown])
    assert broken in selected and unknown in selected


def test_same_concept_metric_outside_requested_period_cannot_disappear():
    summary, index = table_fixture([(1, 1, [["Date", "Total Employees", "Employees"],
        ["2024-01-01", 100, 20], ["2024-02-01", 120, 30]])])
    question = "Employees와 Total Employees의 추이를 비교해줘"
    candidates = trend_candidates(summary, index, question)
    missing = replace(candidates[1], observations=(), context=(candidates[1].observations[0].label,),
                      error="outside_requested_period")
    assert comparison_missing_metrics(question, [candidates[0], missing],
                                      [prepare_trend_candidate(candidates[0], index.rows)]) == ["employees"]
    assert _answer(summary, index, question="Total Employees의 추이를 설명해줘") is None


def test_all_selected_display_translations_are_covered_not_just_first_metric():
    summary, index = table_fixture([(1, 1, [["Date", "Revenue", "Operating Income"],
        ["2024-01-01", 100, 20], ["2024-02-01", 120, 30]])])
    answer = _answer(summary, index, question="매출과 영업이익의 기간별 추이를 비교해줘")
    assert answer.status == "limited"  # Currency is intentionally absent.
    assert answer.verification.level == "source_checked"
    assert "Revenue:" in answer.answer and "Operating Income:" in answer.answer
    assert "원본 시계열과 모두 연결하지 못했습니다" not in answer.answer
