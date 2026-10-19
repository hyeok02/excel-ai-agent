"""Synthetic source-bound time series shared by trend arithmetic tests."""
from datetime import datetime, timedelta

from app.agent.query.index import IndexedCell
from app.agent.query.metric_observation_cells import MetricObservation
from app.agent.query.metric_observation_units import ObservationUnit


def observations(values, dates=None, number_format="General", grain=None, scenario=None):
    label = IndexedCell("Series", "B1", "Metric", None)
    dates = dates or [(datetime(2020, 1, 1) + timedelta(days=index)).isoformat()
                      for index in range(len(values))]
    return [MetricObservation(
        label,
        IndexedCell("Series", f"B{index + 2}", value, None, "number", number_format),
        datetime.fromisoformat(date), IndexedCell("Series", f"A{index + 2}", date, None),
        grain, scenario, (),
    ) for index, (value, date) in enumerate(zip(values, dates))]


def units(items, suffix="명"):
    return [ObservationUnit(suffix, (suffix,), (), True) for _ in items]
