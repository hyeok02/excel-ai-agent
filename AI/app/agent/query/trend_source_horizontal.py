"""Read complete report rows against their explicit horizontal period axis."""
import re
from dataclasses import replace

from openpyxl.utils import coordinate_to_tuple

from app.agent.query.metric_observation_cells import (
    MetricObservation, _column, _human_label, _numeric,
)
from app.agent.query.trend_labels import trend_metric_label_matches as metric_label_matches
from app.agent.query.metric_observation_periods import GRAINS, SCENARIOS, source_period, source_period_grain
from app.agent.query.metric_observations import _axis_qualifier, _intervening_section, _period_cells
from app.agent.query.tabular_catalog_sources import cell_value, source_cells, table_context, table_sources
from app.agent.query.trend_source_context import verified_context
from app.agent.query.trend_source_models import MAX_TREND_OBSERVATIONS, TrendCandidate
from app.agent.query.trend_source_readback import rectangle_rows
from app.agent.query.trend_source_scope import scope_dated_items


def horizontal_candidates(summary, index, question, source_names=()):
    result = []
    for sheet in summary.sheets:
        sheet_cells = {address: cell for region in sheet.regions for address, cell in source_cells(region).items()}
        for reference, raw, complete, _, hidden, _ in table_sources(sheet):
            matches = [cell for cell in raw.values() if isinstance(cell_value(cell), str)
                       and metric_label_matches(cell_value(cell), question)]
            if not matches:
                continue
            rows, error = rectangle_rows(sheet.name, reference, raw, complete, index)
            if error:
                if _horizontal_hint(raw, matches):
                    result.append(TrendCandidate(f"{sheet.name}!{reference}", (), error=error))
                continue
            captions = verified_context(table_context(sheet.name, reference, sheet_cells), index)
            visible = [row for row in rows if row.row_number not in hidden]
            for row in visible:
                labels = [cell for cell in row.cells if _human_label(cell)]
                for label in labels:
                    if not metric_label_matches(str(label.value), question):
                        continue
                    left = _column(label)
                    axes = [(axis, _period_cells(axis)) for axis in visible
                            if 0 < row.row_number - axis.row_number <= 40]
                    dated_columns = {_column(cell) for _, dates in axes for cell in dates}
                    right = min((_column(cell) for cell in labels if _column(cell) > left
                                 and _column(cell) not in dated_columns), default=16385)
                    axes = [(axis, dates) for axis, dates in axes
                            if sum(left < _column(cell) < right for cell in dates) >= 2]
                    if not axes:
                        continue
                    axis, dates = max(axes, key=lambda item: item[0].row_number)
                    if _intervening_section(visible, axis, row, left, right):
                        continue
                    competing = [other for other, _ in axes if other != axis and not any(
                        other.row_number < between.row_number < axis.row_number
                        and any(_column(cell) == left and _human_label(cell) for cell in between.cells)
                        and any(left < _column(cell) < right and _numeric(cell.value) for cell in between.cells)
                        for between in visible)]
                    if competing:
                        result.append(TrendCandidate(f"{sheet.name}!{reference}", (), (label,),
                                                     "ambiguous_date_axis", len(hidden)))
                        continue
                    candidate = _candidate(sheet.name, reference, label, row, axis, dates,
                                           visible, left, right, len(hidden), question, captions or (), source_names)
                    if captions is None:
                        candidate = replace(candidate, error="source_mismatch")
                    else:
                        candidate = replace(candidate, context=(*candidate.context, *captions), observations=tuple(
                            replace(point, entity_cells=captions) for point in candidate.observations))
                    result.append(candidate)
    return result


def _candidate(sheet, reference, label, row, axis, dates, rows, left, right, hidden, question, captions, source_names):
    base = TrendCandidate(f"{sheet}!{reference}", (), (label,), hidden_rows=hidden)
    by_column = {_column(cell): cell for cell in dates if left < _column(cell) < right}
    values = {_column(cell): cell for cell in row.cells if left < _column(cell) < right}
    axis_cells = {_column(cell): cell for cell in axis.cells if left < _column(cell) < right}
    # Missing/invalid dates or values cannot be silently omitted from the trend.
    occupied = set(by_column) | {column for column, cell in values.items()
                               if cell.value not in (None, "") or cell.formula}
    if len(occupied) > MAX_TREND_OBSERVATIONS:
        return replace(base, error="resource_limit")
    occupied, note, error = scope_dated_items(
        question, label, [(column, axis_cells.get(column)) for column in sorted(occupied)], captions,
        source_names=source_names)
    base = replace(base, period_note=note)
    if error:
        return replace(base, error=error)
    observations = []
    for column in sorted(occupied):
        period_cell, value = axis_cells.get(column), values.get(column)
        period = source_period(period_cell.value) if period_cell else None
        if period is None:
            return replace(base, error="missing_or_invalid_date")
        if value is None or not _numeric(value.value):
            return replace(base, error="missing_or_invalid_value")
        grain, grain_refs = _axis_qualifier(rows, axis, by_column, value, left, right, GRAINS)
        grain = grain or source_period_grain(period_cell.value)
        scenario, scenario_refs = _axis_qualifier(rows, axis, by_column, value, left, right, SCENARIOS)
        if isinstance(period_cell.value, str) and re.fullmatch(r"(?:FY\s*)?(?:19|20)\d{2}\s*[AE]", period_cell.value, re.I):
            grain = "annual"
            scenario = "actual" if period_cell.value.strip().casefold().endswith("a") else "estimate"
            grain_refs, scenario_refs = [*grain_refs, period_cell], [*scenario_refs, period_cell]
        observations.append(MetricObservation(label, value, period, period_cell, grain, scenario,
                                              tuple(dict.fromkeys([*grain_refs, *scenario_refs]))))
    return replace(base, observations=tuple(observations),
                   error=None if len(observations) >= 2 else "insufficient_periods")


def _horizontal_hint(raw, matches):
    """Samples may prove an unsafe candidate exists, never prove its answer."""
    for label in matches:
        number, column = coordinate_to_tuple(label["address"])
        axis_counts = {}
        for address, cell in raw.items():
            row, axis_column = coordinate_to_tuple(address)
            if 0 < number - row <= 40 and axis_column > column and source_period(cell_value(cell)):
                axis_counts[row] = axis_counts.get(row, 0) + 1
        if any(count >= 2 for count in axis_counts.values()):
            return True
    return False
