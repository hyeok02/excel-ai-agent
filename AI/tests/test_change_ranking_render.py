"""Human percentage display cannot change exact ordering or hide real movement."""
from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.agent.query.change_ranking_calculations import calculate_ranking
from app.agent.query.change_ranking_render import render_ranking
from app.agent.query.trend_source_models import TrendCandidate
from tests.support.trend_fixtures import observations, units


@pytest.mark.parametrize("after,expected", [
    (Decimal("82.646420824295010845986984815618"), "감소율 약 17.35%"),
    (Decimal("70"), "감소율 30%"),
    (Decimal("99.9999999"), "감소율 약 1.00E-7%"),
])
def test_percentages_are_readable_but_nonzero_rates_never_appear_zero(after, expected):
    points = tuple(replace(point, label=replace(point.label, value="Alpha"))
                   for point in observations([100, after]))
    source = [(TrendCandidate("Series!A1:B3", points), tuple(units(points)))]
    request = SimpleNamespace(basis="net", direction="decrease", percent=True)
    ranking = calculate_ranking(source, request)
    original_ordering = ranking.winners[0].ordering
    text = render_ranking(ranking, request, "부서")
    assert expected in text
    assert "감소율 0%" not in text
    assert ranking.winners[0].ordering == original_ordering
