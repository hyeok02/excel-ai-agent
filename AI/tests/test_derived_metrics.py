from app.services.insights.display.derived_metrics import (
    change_score, derived_metric, magnitude_weight,
)


def test_growth_and_ratio_names_are_derived() -> None:
    assert derived_metric("1 Year Growth (%)  Total Revenue")
    assert derived_metric("CAGR (5 Year) EBITDA")
    assert derived_metric("TEV / Revenue")
    assert derived_metric("영업이익률")


def test_measured_names_are_not_derived() -> None:
    assert not derived_metric("Revenue")
    assert not derived_metric("Net Income")
    assert not derived_metric("전체 직원 수")


def test_percent_formatting_marks_a_derived_figure() -> None:
    assert derived_metric("Revenue", [{"number_format": "0.0%"}])
    assert not derived_metric("Revenue", [{"number_format": "#,##0"}])


def test_magnitude_weight_grows_with_size() -> None:
    assert magnitude_weight(4.725) < magnitude_weight(713163)
    assert magnitude_weight(None) == 0
    assert magnitude_weight(0.4) == 0


def test_absolute_change_outranks_a_larger_rate_change() -> None:
    growth = {"metric": "1 Year Growth (%) Total Revenue", "latest_value": 4.725,
              "change_rate_percent": -21.6}
    revenue = {"metric": "Revenue", "latest_value": 713163,
               "change_rate_percent": 10.0}
    assert max([growth, revenue], key=change_score) is revenue
