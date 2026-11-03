"""Sums and means of float cells are shown at a readable precision, not with binary noise."""
from decimal import Decimal

from app.agent.query.excel_number_formats import parse_number_format
from app.agent.query.streaming_tabular_numeric import NumericAccumulator
from app.agent.query.tabular_numeric import _render

GENERAL = parse_number_format("General")


def test_float_noise_and_long_means_are_cut() -> None:
    result = NumericAccumulator()
    for value in [33.6, 817.92, 0.1 + 0.2]:
        assert result.add(value, "General")
    text = result.render("all")
    assert "합계 851.82" in text and "평균 283.94" in text and "최솟값 0.3," in text
    assert "0000" not in text


def test_small_values_keep_three_significant_digits_and_huge_values_stay_exact() -> None:
    assert _render(Decimal("0.00123456"), GENERAL) == "0.00123"
    assert _render(Decimal("-0.5"), GENERAL) == "-0.5"
    assert _render(Decimal(10 ** 35 + 1), GENERAL) == f"{10 ** 35 + 1:,}"
