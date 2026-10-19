"""Discover source-bound time series without workbook-specific names or ranges."""
from app.agent.query.metric_observation_cells import _DATE_HEADER
from app.agent.query.trend_labels import trend_metric_label_matches as metric_label_matches
from app.agent.query.metric_observation_periods import source_period
from app.agent.query.tabular_catalog import build_query_tables
from app.agent.query.trend_source_horizontal import horizontal_candidates
from app.agent.query.trend_source_vertical import vertical_candidate
from app.agent.query.trend_source_models import TrendCandidate


def trend_candidates(summary, index, question) -> list[TrendCandidate]:
    tables = build_query_tables(summary)
    result = []
    for table in tables:
        # Non-temporal summary tables are not failed alternatives to a time series.
        dated = any(_DATE_HEADER.search(column.header) or sum(
            isinstance(value, str) and source_period(value) is not None for value in column.sample_values) >= 2
                    for column in table.columns)
        if not dated:
            continue
        for metric in table.columns:
            if metric_label_matches(metric.header, question):
                result.append(vertical_candidate(table, metric, tables, index, question))
    result.extend(horizontal_candidates(summary, index, question))
    return result
