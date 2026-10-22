"""Chronological ranking cannot silently change the question's baseline."""
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.agent.query.change_ranking_calculations import calculate_ranking
from app.agent.query.change_ranking_render import render_ranking
from app.agent.query.trend_source_models import TrendCandidate
from tests.support.trend_fixtures import observations, units


def request(basis="auto", direction="decrease", percent=False):
    return SimpleNamespace(basis=basis, direction=direction, percent=percent)


def series(*groups):
    result = []
    for name, values in groups:
        points = tuple(replace(item, label=replace(item.label, value=name)) for item in observations(values))
        result.append((TrendCandidate("Series!A1:C20", points), tuple(units(points))))
    return tuple(result)


@pytest.mark.parametrize("basis,name,amount,end", [
    ("auto", "Alpha", 80, 2), ("net", "Beta", 30, 2),
    ("extreme_to_latest", "Alpha", 80, 2), ("adjacent", "Alpha", 80, 2),
])
def test_explicit_baseline_and_auto(basis, name, amount, end):
    result = calculate_ranking(series(("Alpha", [100, 200, 120]), ("Beta", [100, 100, 70])), request(basis))
    assert len(result.winners) == 1
    winner = result.winners[0]
    assert winner.candidate.observations[0].label.value == name
    assert winner.score == amount and winner.end == end


def test_drawdown_must_follow_peak_and_peak_latest_is_separate():
    data = series(("Alpha", [30, 100, 80, 90]))
    drawdown = calculate_ranking(data, request()).winners[0]
    latest = calculate_ranking(data, request("extreme_to_latest")).winners[0]
    assert (drawdown.start, drawdown.end, drawdown.score) == (1, 2, 20)
    assert (latest.start, latest.end, latest.score) == (1, 3, 10)
    assert not calculate_ranking(data, request("net")).winners


def test_adjacent_does_not_become_peak_to_trough():
    data = series(("Alpha", [100, 200, 180, 120, 130]))
    assert calculate_ranking(data, request()).winners[0].score == 80
    adjacent = calculate_ranking(data, request("adjacent")).winners[0]
    assert (adjacent.start, adjacent.end, adjacent.score) == (2, 3, 60)


def test_rise_requires_low_before_high():
    data = series(("Alpha", [100, 30, 50, 40]))
    result = calculate_ranking(data, request(direction="increase")).winners[0]
    assert (result.start, result.end, result.score) == (1, 2, 20)


def test_every_group_tie_is_preserved_and_rendered():
    data = series(("Alpha", [100, 80, 90]), ("Beta", [80, 60, 70]), ("Gamma", [60, 50, 55]))
    result = calculate_ranking(data, request())
    text = render_ranking(result, request(), "부서", calculate_ranking(data, request(), "net"))
    assert len(result.winners) == 2 and "공동 1위 2개" in text
    assert "Alpha, Beta" in text and "Gamma" in text


def test_auto_explains_no_net_decline_without_hiding_period_drawdown():
    data = series(("Alpha", [30, 100, 80, 90]), ("Beta", [20, 30, 25, 28]))
    result = calculate_ranking(data, request())
    text = render_ranking(result, request(), "부서", calculate_ranking(data, request(), "net"))
    assert "Alpha" in text and "20명 감소" in text
    assert "전체 기간 시작→끝 기준으로는 감소한 부서가 없습니다" in text
    assert "2개 부서 모두 증가" in text


def test_percentage_ranking_uses_baseline_not_raw_difference():
    data = series(("Alpha", [1000, 900]), ("Beta", [100, 80]))
    assert calculate_ranking(data, request("net")).winners[0].score == 100
    rate = calculate_ranking(data, request("net", percent=True))
    assert rate.winners[0].candidate.observations[0].label.value == "Beta"
    assert rate.winners[0].score == 20


@pytest.mark.parametrize("values", [[0, 1, 2], [-1, 0, 1], [10, 0, 20]])
def test_undefined_percentages_never_skip_members(values):
    with pytest.raises(ValueError, match="0 이하"):
        calculate_ranking(series(("Alpha", values)), request(percent=True))


def test_net_percentage_does_not_require_intermediate_values_as_baselines():
    result = calculate_ranking(series(("Alpha", [100, 0, 80])), request("net", percent=True))
    assert result.winners[0].score == 20


def test_peak_latest_percentage_uses_selected_positive_peak():
    result = calculate_ranking(series(("Alpha", [100, 0, 80])), request("extreme_to_latest", percent=True))
    assert result.winners[0].score == 20


def test_maximum_increase_percentage_preserves_low_before_high():
    result = calculate_ranking(series(("Alpha", [100, 20, 40])), request(direction="increase", percent=True))
    assert (result.winners[0].start, result.winners[0].end, result.winners[0].score) == (1, 2, 100)


def test_percentage_decline_crossing_zero_uses_actual_largest_rate():
    result = calculate_ranking(series(("Alpha", [100, 10, -10])), request(percent=True))
    assert (result.winners[0].start, result.winners[0].end, result.winners[0].score) == (1, 2, 200)


@pytest.mark.parametrize("broken", [None, True, float("nan"), float("inf")])
def test_missing_or_invalid_group_value_blocks_whole_rank(broken):
    with pytest.raises(ValueError):
        calculate_ranking(series(("Alpha", [100, broken, 80]), ("Beta", [30, 20, 10])), request())


def test_tiny_changes_and_huge_values_are_exact():
    high = Decimal("1" + "0" * 100 + ".0000001")
    low = Decimal("1e100")
    result = calculate_ranking(series(("Alpha", [high, low])), request())
    assert result.winners[0].score == Decimal(".0000001")


def test_percentage_rounding_cannot_create_a_false_tie():
    baseline = Decimal("1e100")
    larger = Decimal("1" + "0" * 99 + "1")
    result = calculate_ranking(series(("Alpha", [baseline, 1]), ("Beta", [larger, 1])), request("net", percent=True))
    assert len(result.winners) == 1 and result.winners[0].candidate.observations[0].label.value == "Beta"


@pytest.mark.parametrize("change", ["order", "length", "unit", "error"])
def test_unaligned_or_incomplete_sources_not_certified(change):
    data = list(series(("Alpha", [100, 80]), ("Beta", [30, 20])))
    candidate, source_units = data[1]
    if change == "order":
        candidate = replace(candidate, observations=tuple(reversed(candidate.observations)))
    elif change == "length":
        source_units = source_units[:-1]
    elif change == "unit":
        source_units = tuple(replace(unit, identity=("USD",)) for unit in source_units)
    else:
        candidate = replace(candidate, error="missing_or_invalid_value")
    data[1] = candidate, source_units
    with pytest.raises(ValueError):
        calculate_ranking(data, request())
