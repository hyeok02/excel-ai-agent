"""Threshold interpretation never rounds a long quantity into another condition."""
from decimal import Decimal

import pytest

from app.agent.query.tabular_quantity import parse_quantity
from tests.test_advanced_request_unit_safety import run


@pytest.mark.parametrize("text,expected", [
    ("1천3백만", 13_000_000), ("1억2천3백만", 123_000_000),
    ("-1억2천3백만", -123_000_000), ("1.5천만", 15_000_000),
    ("3백5십2", 352), ("1십억", 1_000_000_000),
])
def test_small_and_large_korean_units_have_positional_value(text, expected):
    assert parse_quantity(text) == Decimal(expected)


@pytest.mark.parametrize("text", ["1천2천", "1백2천", "1만2억", "1 2"])
def test_invalid_unit_order_or_adjacent_numbers_are_not_guessed(text):
    assert parse_quantity(text) is None


def test_english_magnitude_preserves_all_decimal_digits():
    integer = 10 ** 30 + 1
    question = f"sum 매출 by 부서 having sum 매출 > ${integer} million"
    assert run(question, "매출(USD)", integer * 10 ** 6)
    assert not run(question, "매출(USD)", 10 ** 36)
