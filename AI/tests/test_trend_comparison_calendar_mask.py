"""Unrelated source prose must not erase a real requested comparison window."""
import pytest
from dataclasses import replace

from app.agent.query.trend_comparison import comparison_answer
from app.agent.query.trend_selection import prepare_trend_candidate
from app.agent.query.trend_sources import trend_candidates
from tests.support.large_workbook_fixtures import offline
from tests.support.trend_adversarial_fixtures import direct
from tests.tabular_query_fixtures import table_fixture

_METRICS = "Total Employees와 Temporary Employees의 기간별 추이를 비교해줘"


def _source(note=None, horizontal=False):
    rows = [["Date", "Total Employees", "Temporary Employees"],
            ["2023-12-31", 9000, 8000], ["2024-01-31", 100, 10],
            ["2024-02-29", 150, 20], ["2024-03-31", 120, 50]]
    if horizontal:
        rows = [list(row) for row in zip(*rows)]
        rows[0][0] = "Metric"
    blocks = [(1, 1, rows)]
    if note:
        blocks.append((10, 1 if horizontal else 8, [[note]]))
    return table_fixture(blocks)


@pytest.mark.parametrize("window", ["2024년 이후", "2024년부터", "2024-01-01 이후"])
@pytest.mark.parametrize("horizontal", [False, True])
def test_unrelated_literal_note_does_not_mask_requested_multi_metric_date_window(window, horizontal):
    summary, index = _source(window, horizontal)
    answer = direct(summary, index, window + " " + _METRICS)
    assert answer.status == "answered", answer.model_dump()
    assert answer.verification.level == "request_checked"
    assert answer.answer.count("3개 관측값") == 2, answer.answer
    assert "2023-12-31" not in answer.answer and "9,000" not in answer.answer
    excluded = {"B2", "B3"} if horizontal else {"B2", "C2"}
    assert not excluded & {item.reference for item in answer.evidence}


def test_comparison_checks_prepared_points_against_final_request_window():
    summary, index = _source()
    # Simulate an upstream hint removing the date phrase before extraction.
    # The final comparison must independently reject or apply the real window.
    candidates = trend_candidates(summary, index, _METRICS)
    prepared = [prepare_trend_candidate(candidate, index.rows) for candidate in candidates]
    answer = comparison_answer("2024년 이후 " + _METRICS, prepared, index.rows, set(), summary, index)
    assert answer is not None
    if answer.status in {"answered", "limited"}:
        assert "2023-12-31" not in answer.answer, answer.model_dump()
        assert not {"B2", "C2"} & {item.reference for item in answer.evidence}


def test_final_comparison_rejects_an_upstream_narrower_window_as_full_history():
    summary, index = _source()
    candidates = trend_candidates(summary, index, "2024년 " + _METRICS)
    prepared = [prepare_trend_candidate(candidate, index.rows) for candidate in candidates]
    answer = comparison_answer(_METRICS, prepared, index.rows, set(), summary, index)
    assert answer.status == "insufficient_evidence"
    assert answer.verification.level != "request_checked"


def test_relative_comparison_keeps_each_series_original_latest_anchor():
    summary, index = _source()
    candidates = trend_candidates(summary, index, _METRICS)
    prepared = [prepare_trend_candidate(candidate, index.rows) for candidate in candidates]
    second, units = prepared[1]
    prepared[1] = (replace(second, observations=second.observations[:-1]), units[:-1])
    answer = comparison_answer("최근 6개월 " + _METRICS, prepared, index.rows, set(), summary, index)
    assert answer.status == "limited" and answer.verification.level == "source_checked"
    assert "최신 관측일 2024-03-31 기준" in answer.answer
    assert "최신 관측일 2024-02-29 기준" in answer.answer
    assert "마지막 관측값 차이" not in answer.answer
