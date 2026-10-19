"""The complete path, not source row order or net sign, determines a trend."""
from dataclasses import replace
from decimal import Decimal

import pytest

from app.agent.query.trend_calculations import calculate_trend, change_percent, exact_difference
from tests.support.trend_fixtures import observations


@pytest.mark.parametrize("values,directions,reversals", [
    ([1, 2, 3], [1], [False]), ([3, 2, 1], [-1], [False]),
    ([2, 2, 2], [0], [False]), ([1, 3, 1], [1, -1], [False, True]),
    ([3, 1, 2], [-1, 1], [False, True]),
    ([1, 2, 2, 3], [1, 0, 1], [False, False, False]),
    ([3, 1, 1, 2], [-1, 0, 1], [False, False, True]),
    ([1, 1, 2], [0, 1], [False, False]),
])
def test_runs_and_reversals(values, directions, reversals):
    profile = calculate_trend(observations(values))
    assert [run.direction for run in profile.runs] == directions
    assert [run.reversal for run in profile.runs] == reversals
    assert profile.rising + profile.falling + profile.flat == len(values) - 1
    assert profile.runs[0].start == 0 and profile.runs[-1].end == len(values) - 1


def test_source_order_does_not_change_chronology():
    source = observations([763, 1277, 1070, 1081])
    expected = calculate_trend(source)
    assert calculate_trend(list(reversed(source))) == expected
    assert calculate_trend([source[2], source[0], source[3], source[1]]) == expected


def test_all_tied_extrema_preserved():
    profile = calculate_trend(observations([1, 3, 1, 3, 1]))
    assert profile.minimum == (0, 2, 4)
    assert profile.maximum == (1, 3)


@pytest.mark.parametrize("value", [None, True, float("nan"), float("inf"), "not numeric"])
def test_unusable_observations_are_never_skipped(value):
    with pytest.raises(ValueError):
        calculate_trend(observations([1, value, 3]))


def test_duplicate_dates_or_single_point_rejected():
    source = observations([1, 2])
    with pytest.raises(ValueError):
        calculate_trend([source[0]])
    with pytest.raises(ValueError):
        calculate_trend([source[0], replace(source[1], period=source[0].period)])


def test_tiny_changes_remain_real_changes():
    before, after = Decimal("1e100"), Decimal("1" + "0" * 100 + ".0000001")
    assert exact_difference(before, after) == Decimal(".0000001")
    profile = calculate_trend(observations([before, after, before]))
    assert (profile.rising, profile.falling, profile.flat) == (1, 1, 0)


@pytest.mark.parametrize("before", [Decimal(0), Decimal(-100)])
def test_nonpositive_baseline_has_no_growth_percentage(before):
    assert change_percent(before, Decimal(50)) is None


def test_positive_baseline_signed_growth():
    assert change_percent(Decimal(100), Decimal(80)) == Decimal(-20)
    assert change_percent(Decimal(100), Decimal(120)) == Decimal(20)
