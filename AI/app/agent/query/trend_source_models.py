"""A complete, source-addressed series or an explicit reason it is unsafe."""
from dataclasses import dataclass

from app.agent.query.index import IndexedCell
from app.agent.query.metric_observation_cells import MetricObservation

MAX_TREND_OBSERVATIONS = 20_000


@dataclass(frozen=True)
class TrendCandidate:
    table_id: str
    observations: tuple[MetricObservation, ...]
    context: tuple[IndexedCell, ...] = ()
    error: str | None = None
    hidden_rows: int = 0
    period_note: str = ""
