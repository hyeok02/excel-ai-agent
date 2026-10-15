from datetime import datetime

import pytest

from app.agent.query.metric_observation_units import observation_unit
from app.agent.query.metric_observations import MetricObservation
from tests.test_metric_observation_answers import _index


def _unit(source, label="A3", value="B3", number_format="General"):
    index = _index({"Arbitrary": source}, {("Arbitrary", value): number_format})
    cells = {cell.address: cell for row in index.rows for cell in row.cells}
    item = MetricObservation(cells[label], cells[value], datetime.min, cells[label], None, None, ())
    return observation_unit(item, list(index.rows))


def test_parallel_currency_controls_bind_to_the_correct_block():
    source = {"A1": "Currency", "A2": "USD", "D1": "Currency", "D2": "EUR",
              "A3": "Revenue", "B3": 110, "D3": "Cost", "E3": 55}
    left, right = _unit(source), _unit(source, "D3", "E3")
    assert left.known and left.suffix == "미국 달러"
    assert right.known and right.suffix == "유로"
    assert {cell.address for cell in left.references} == {"A1", "A2"}
    assert {cell.address for cell in right.references} == {"D1", "D2"}


def test_parallel_currency_and_magnitude_controls_do_not_cross_populations():
    source = {"A1": "Currency", "A2": "USD", "B1": "Magnitude", "B2": "Millions",
              "D1": "Currency", "D2": "EUR", "E1": "Magnitude", "E2": "Thousands",
              "A3": "Revenue", "B3": 110, "D3": "Cost", "E3": 55}
    assert _unit(source).suffix == "백만 미국 달러"
    assert _unit(source, "D3", "E3").suffix == "천 유로"


def test_parallel_controls_at_different_row_heights_do_not_override_left_table():
    source = {"A1": "Currency", "A2": "USD", "D2": "Currency", "D3": "EUR",
              "A5": "Revenue", "B5": 110, "D5": "Cost", "E5": 55}
    assert _unit(source, "A5", "B5").suffix == "미국 달러"
    assert _unit(source, "D5", "E5").suffix == "유로"


def test_currency_format_preserves_caption_magnitude():
    unit = _unit({"A1": "Amounts in USD millions", "A3": "Revenue", "B3": 110}, number_format="$#,##0")
    assert unit.known and unit.suffix == "백만 미국 달러"
    assert {cell.address for cell in unit.references} == {"A1"}


@pytest.mark.parametrize("caption,expected", [
    ("Amounts ($000)", "천 달러"), ("Amount (USD 000)", "천 미국 달러"),
    ("단위: 백만원", "백만 원"), ("단위: 억원", "억 원"),
])
def test_common_caption_units_are_preserved(caption, expected):
    unit = _unit({"A1": caption, "A3": "Revenue", "B3": 110})
    assert unit.known and unit.suffix == expected


@pytest.mark.parametrize("number_format", ["$#,##0", '"€"#,##0'])
def test_conflicting_format_and_source_currency_cannot_be_verified(number_format):
    caption = "Amounts in EUR millions" if "$" in number_format else "Amounts in USD millions"
    unit = _unit({"A1": caption, "A3": "Revenue", "B3": 110}, number_format=number_format)
    assert not unit.known
    assert unit.identity[0] == "conflicting_units"


def test_explicit_metric_unit_overrides_an_incompatible_report_magnitude():
    source = {"A1": "Amounts in USD millions", "A3": "Revenue ($000)", "B3": 110}
    assert _unit(source).suffix == "천 달러"
