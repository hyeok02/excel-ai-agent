"""User-facing trends explicitly separate endpoints, reversals and latest move."""
from dataclasses import replace
from decimal import Decimal

import pytest

from app.agent.query.trend_render import render_trend, trend_witness_indices
from tests.support.trend_fixtures import observations, units


def answer(values, **kwargs):
    source = observations(values, **kwargs)
    return render_trend(source, units(source))


def test_total_growth_does_not_hide_decline_from_peak():
    text = answer([3955, 6101, 5417], dates=["2020-09-01", "2023-09-01", "2025-06-01"])
    assert "1,462명 증가(+36.97%)" in text
    assert "684명 감소(-11.21%)" in text
    assert "상승 뒤 하락 전환" in text
    assert "최고값: 6,101명, 2023-09-01" in text
    assert "지속적인 상승·하락을 뜻하지는 않습니다" in text


def test_services_rebound_is_not_continuous_increase():
    text = answer([763, 1277, 1070, 1081], dates=[
        "2020-09-01", "2023-09-01", "2025-03-01", "2025-06-01"])
    assert "318명 증가(+41.68%)" in text
    assert "하락 뒤 반등" in text and "상승 뒤 하락 전환" in text
    assert "최근 관측 구간: 2025-03-01 → 2025-06-01, 1,070명 → 1,081명, 11명 증가(+1.03%)" in text
    assert "분기" not in text


def test_equal_endpoints_do_not_hide_midpoint_motion():
    text = answer([100, 200, 100])
    assert "전체 시작·끝 비교: 100명 → 100명, 변동 없음" in text
    assert "상승 1회, 하락 1회, 보합 0회" in text
    assert "최저값: 100명" in text and "동률 2개 시점" in text


def test_flat_does_not_create_false_rebound():
    assert "반등" not in answer([1, 2, 2, 3])
    assert "반등" in answer([3, 2, 2, 3])
    assert "반등" not in answer([2, 2, 3])


def test_negative_and_zero_baseline_disclose_no_percentage():
    for values in ([-10, -5], [0, 5]):
        text = answer(values)
        assert "%" not in text
        assert "시작값이 0 이하인 구간은 증감률을 계산하지 않았습니다" in text


def test_percent_format_displays_percentage_points_not_growth_rates():
    text = answer([.20, .25, .22], number_format="0.0%")
    assert "20% → 22%, 2%p 증가" in text
    assert "5%p 증가" in text and "3%p 감소" in text
    assert "명" not in text and "(+" not in text


def test_tiny_movements_never_render_as_zero():
    text = answer([Decimal("1"), Decimal("1.000000000000000000001")])
    assert "0.000000000000000000001명 증가" in text
    assert "+1.00E-19%" in text
    assert "0명 증가" not in text and "+0%" not in text


def test_bounded_output_discloses_omitted_runs_and_tied_dates():
    text = answer([1, 2] * 100)
    assert "중간 187개 구간의 상세 표시는 생략" in text
    assert "전체 관측값은 계산에 포함" in text
    assert "상승 100회, 하락 99회, 보합 0회" in text
    assert "동률 100개 시점" in text and "외 94개 시점" in text
    assert len(text) < 5000


def test_shuffled_values_render_identically():
    source = observations([1, 5, 3, 4])
    assert render_trend(source, units(source)) == render_trend(source[::-1], units(source))


def test_year_only_source_does_not_invent_january_first():
    source = observations([100, 110], dates=["2020-01-01", "2021-01-01"], grain="annual")
    source = [replace(item, period_cell=replace(item.period_cell, value=str(item.period.year)))
              for item in source]
    text = render_trend(source, units(source))
    assert "2020년(연간)" in text and "2020-01-01" not in text


def test_incompatible_units_are_not_rendered():
    source = observations([1, 2])
    source_units = units(source)
    source_units[1] = replace(source_units[1], identity=("USD",))
    with pytest.raises(ValueError):
        render_trend(source, source_units)


def test_displayed_periods_and_values_all_have_witnesses():
    source = observations([1, 2] * 100)
    text = render_trend(source, units(source))
    indices = trend_witness_indices(source)
    assert {0, 198, 199}.issubset(indices)
    for index, item in enumerate(source):
        if item.period.date().isoformat() in text:
            assert index in indices
    assert len(indices) <= 40


def test_excel_scaled_numbers_keep_correct_delta_and_growth_rate():
    text = answer([1_000_000, 2_000_000], number_format='0.0,,"백만"')
    assert "1백만 → 2백만, 1백만 증가(+100%)" in text


def test_source_intraday_observations_preserve_time():
    text = answer([2, 3], dates=["2020-01-01T09:00:00", "2020-01-01T17:00:00"])
    assert "2020-01-01 09:00:00 → 2020-01-01 17:00:00" in text


def test_huge_baseline_does_not_round_away_tiny_movement():
    text = answer([Decimal("1e100"), Decimal("1" + "0" * 100 + ".0000001")])
    assert "0.0000001명 증가" in text
    assert "변동 없음" not in text
