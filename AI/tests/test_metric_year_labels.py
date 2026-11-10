"""A value read under a year header is dated by that year, not by an invented 1 January."""
from datetime import datetime
from types import SimpleNamespace

from app.agent.query.metric_observation_render import _period_label


def _item(source, period):
    return SimpleNamespace(period=period, period_cell=SimpleNamespace(value=source), grain=None, scenario=None)


def test_year_headers_read_as_years_and_dates_keep_their_day():
    assert _period_label(_item(2019, datetime(2019, 1, 1))) == "2019년 기준"
    assert _period_label(_item("2019", datetime(2019, 1, 1))) == "2019년 기준"
    assert _period_label(_item(datetime(2019, 1, 1), datetime(2019, 1, 1))) == "2019년 1월 1일 기준"
    assert _period_label(_item("2019-03", datetime(2019, 3, 1))) == "2019년 3월 기준"
