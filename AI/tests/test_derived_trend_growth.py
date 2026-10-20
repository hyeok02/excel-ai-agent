"""Growth trajectories use exact source baselines without model calls."""
import pytest

from app.agent.query.derived_trend_answers import derived_trend_answer
from tests.support.large_workbook_fixtures import offline
from tests.support.trend_scoped_fixtures import refused, series


def _answer(rows, question="Total Employees 증감률 추이를 설명해줘", layout="vertical"):
    summary, index = series(rows, layout)
    return derived_trend_answer(question, summary, index)


def _checked(answer):
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked"
    assert {"operand_lineage", "positive_denominator", "request_alignment"} <= set(answer.verification.checks)


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_previous_observation_growth_has_its_own_rebound(layout):
    rows = [["2024-03-31", 180], ["2024-01-31", 100], ["2024-04-30", 270], ["2024-02-29", 200]]
    answer = _answer(rows, layout=layout)
    _checked(answer)
    assert "2024-02-29: 100%" in answer.answer and "2024-03-31: -10%" in answer.answer
    assert "2024-04-30: 50%" in answer.answer and "하락 뒤 반등" in answer.answer
    assert "이전 관측값" in answer.answer and "최초 1개 관측" in answer.answer
    assert "100% → 50%, 50%p 감소" in answer.answer


def test_increasing_amount_can_have_decreasing_growth_rate():
    answer = _answer([["2024-01-31", 100], ["2024-02-29", 120], ["2024-03-31", 132]])
    _checked(answer)
    assert "20% → 10%, 10%p 감소" in answer.answer
    assert "원본 금액·인원의 증감과 증감률 자체" in answer.answer


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_yoy_window_reads_prior_year_and_preserves_original_evidence(layout):
    rows = [["2022-01-31", None], ["2023-01-31", 100], ["2023-02-28", 200],
            ["2024-01-31", 150], ["2024-02-29", 240], ["2025-01-31", None]]
    answer = _answer(rows, "2024년 Total Employees 전년 동기 대비 증감률 추이를 설명해줘", layout)
    _checked(answer)
    assert "2024-01-31: 50% (비교 기준일 2023-01-31)" in answer.answer
    assert "2024-02-29: 20% (비교 기준일 2023-02-28)" in answer.answer
    assert {100, 200, 150, 240} <= {item.value for item in answer.evidence}
    assert "2022-01-31" not in answer.answer and "2025-01-31" not in answer.answer


def test_mom_uses_month_end_and_not_the_previous_available_month():
    answer = _answer([["2024-01-31", 100], ["2024-02-29", 150], ["2024-03-31", 120]],
                     "Total Employees 전월 대비 증감률 추이를 설명해줘")
    _checked(answer)
    assert "2024-02-29: 50%" in answer.answer and "2024-03-31: -20%" in answer.answer
    refused(_answer([["2024-01-31", 100], ["2024-02-29", 150], ["2024-04-30", 120]],
                    "Total Employees 전월 대비 증감률 추이를 설명해줘"))


def test_nonexistent_same_calendar_day_does_not_clamp_to_nearest_day():
    refused(_answer([["2024-01-29", 100], ["2024-02-29", 150], ["2024-03-30", 120]],
                    "Total Employees 전월 대비 증감률 추이를 설명해줘"))


@pytest.mark.parametrize("bad", [0, -10, None, "missing", "=MISSING_CACHE()"])
def test_missing_or_nonpositive_growth_baseline_never_certified(bad):
    refused(_answer([["2024-01-31", bad], ["2024-02-29", 150], ["2024-03-31", 120]]))


def test_explicit_window_cannot_drop_its_first_missing_yoy_base():
    rows = [["2023-02-28", 100], ["2023-03-31", 100], ["2024-01-31", 110],
            ["2024-02-29", 120], ["2024-03-31", 130]]
    refused(_answer(rows, "2024년 Total Employees 전년 동기 대비 증감률 추이를 설명해줘"))


def test_decrease_rate_uses_the_requested_direction_not_growth_sign():
    answer = _answer([["2024-01-31", 100], ["2024-02-29", 80], ["2024-03-31", 40]],
                     "Total Employees 감소율 추이를 설명해줘")
    _checked(answer)
    assert "20% → 50%, 30%p 증가" in answer.answer
    assert "이전 기준값 - 현재값" in answer.answer


def test_relative_output_window_does_not_move_when_baseline_is_loaded():
    rows = [["2023-01-31", 100], ["2023-02-28", 100], ["2023-03-31", 100],
            ["2024-01-31", 120], ["2024-02-29", 130], ["2024-03-31", 140]]
    answer = _answer(rows, "최근 2개월 Total Employees 전년 동기 대비 증감률 추이를 설명해줘")
    _checked(answer)
    assert "최신 관측일 2024-03-31" in answer.answer and "3개 시점" in answer.answer


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_previous_baseline_reads_only_immediate_history_not_unrelated_bad_old_values(layout):
    rows = [["2022-01-31", None], ["2023-12-31", 100], ["2024-01-31", 150],
            ["2024-02-29", 120], ["2025-01-31", None]]
    answer = _answer(rows, "2024년 Total Employees 이전 관측값 대비 증감률 추이를 설명해줘", layout)
    _checked(answer)
    assert "2024-01-31: 50% (비교 기준일 2023-12-31)" in answer.answer
    assert "2024-02-29: -20%" in answer.answer
    assert "2022-01-31" not in answer.answer


@pytest.mark.parametrize("layout", ["vertical", "horizontal"])
def test_previous_baseline_cannot_skip_the_actual_missing_prior_value(layout):
    rows = [["2022-01-31", 100], ["2023-12-31", None], ["2024-01-31", 150], ["2024-02-29", 120]]
    refused(_answer(rows, "2024년 Total Employees 이전 관측값 대비 증감률 추이를 설명해줘", layout))
