"""Extract horizontal report values with source period/grain/scenario cells."""
import re
from app.agent.query.index import IndexedRow
from app.agent.query.metric_observation_periods import GRAINS, SCENARIOS, qualifier, source_period
from app.agent.query.metric_observation_cells import (
    MetricObservation, _DATE_HEADER, _human_label, _column, _numeric,
    _sheet_rows, _text_in_question, _normal, metric_label_matches,
)
from app.agent.query.metric_record_observations import dated_record_observations

def horizontal_observations(rows: list[IndexedRow], question: str) -> list[MetricObservation]:
    sheets = _sheet_rows(rows)
    observations = []
    for sheet_rows in sheets.values():
        axes = [(row, _period_cells(row)) for row in sheet_rows]
        axes = [(row, cells) for row, cells in axes if len(cells) >= 2]
        for row in sheet_rows:
            labels = [cell for cell in row.cells if _human_label(cell)]
            for label in labels:
                if not metric_label_matches(str(label.value), question):
                    continue
                left = _column(label)
                right = min((_column(cell) for cell in labels if _column(cell) > left), default=16_385)
                values = [cell for cell in row.cells if left < _column(cell) < right
                          and (_numeric(cell.value) or cell.formula and cell.value is None)]
                if not values:
                    continue
                previous = [(axis, dates) for axis, dates in axes
                            if 0 < row.row_number - axis.row_number <= 40
                            and sum(left < _column(cell) < right for cell in dates) >= 2]
                if not previous:
                    continue
                axis, dates = max(previous, key=lambda item: item[0].row_number)
                by_column = {_column(cell): cell for cell in dates if left < _column(cell) < right}
                # A new non-date section heading closes the old table. In
                # particular, Revenue in a growth-rate block is not Revenue.
                if _intervening_section(sheet_rows, axis, row, left, right):
                    continue
                for value in values:
                    date_cell = by_column.get(_column(value))
                    if date_cell is None:
                        continue
                    grain, grain_refs = _axis_qualifier(sheet_rows, axis, by_column, value, left, right, GRAINS)
                    scenario, scenario_refs = _axis_qualifier(sheet_rows, axis, by_column, value, left, right, SCENARIOS)
                    if isinstance(date_cell.value, str) and re.fullmatch(r"(?:FY\s*)?(?:19|20)\d{2}\s*[AE]", date_cell.value, re.I):
                        grain = "annual"
                        scenario = "actual" if date_cell.value.strip().casefold().endswith("a") else "estimate"
                        grain_refs = [*grain_refs, date_cell]
                        scenario_refs = [*scenario_refs, date_cell]
                    observations.append(MetricObservation(
                        label, value, source_period(date_cell.value), date_cell, grain, scenario,
                        tuple(dict.fromkeys([*grain_refs, *scenario_refs])),
                    ))
    return observations

def _axis_qualifier(rows, axis, dates, value, left, right, patterns):
    result, references = None, []
    for row in rows:
        if not 0 < axis.row_number - row.row_number <= 3:
            continue
        marked = [(cell, qualifier(cell.value, patterns)) for cell in row.cells
                  if left <= _column(cell) < right
                  and (qualifier(cell.value, GRAINS) or qualifier(cell.value, SCENARIOS))]
        if not marked:
            continue
        before = [(cell, kind) for cell, kind in marked if _column(cell) <= _column(value)]
        # Centered annual captions can start one column after their first date.
        chosen = max(before, key=lambda item: _column(item[0])) if before else min(
            marked, key=lambda item: _column(item[0]))
        if not before and _column(chosen[0]) > min(dates) + 1:
            continue
        if chosen[1] is not None:
            result = chosen[1]
            references = [chosen[0]]
    return result, references

def _intervening_section(rows, axis, data, left, right):
    for row in rows:
        if not axis.row_number < row.row_number < data.row_number:
            continue
        segment = [cell for cell in row.cells if left <= _column(cell) < right]
        texts = [cell for cell in segment if _human_label(cell)]
        numeric = [cell for cell in segment if _numeric(cell.value)]
        if texts and not numeric and any(_column(cell) == left for cell in texts):
            return True
    return False

def _period_cells(row):
    found = [cell for cell in row.cells if source_period(cell.value)]
    if not found:
        return []
    explicit = any(isinstance(cell.value, str) and not re.fullmatch(r"\d{4}", cell.value)
                   for cell in found)
    header = any(isinstance(cell.value, str) and _DATE_HEADER.search(cell.value)
                 for cell in row.cells if cell not in found)
    return found if explicit or header else []
