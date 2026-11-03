"""Extract metric series whose dates run horizontally across worksheet regions."""
from collections import defaultdict
import re

from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

from app.services.insights.display.display_quality import business_priority, is_presentable_label, is_identifier_label
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.narratives.narrative_values import finite
from app.services.insights.facts.series_scalars import unit
from app.services.insights.facts.horizontal_context import axis_dates, declared_axis_unit, period_label
from app.services.insights.narratives.narrative_values import overall

MAX_SERIES = 24
MAX_AXIS_DISTANCE = 120


def extract_horizontal_series(regions):
    rows = _worksheet_rows(regions)
    axes = [axis for row, cells in sorted(rows.items()) for axis in _axes(row, cells, rows)]
    results = []
    for axis_row, axis in axes:
        next_row = min((row for row, _ in axes if row > axis_row), default=10**9)
        results.extend(_axis_series(
            rows, axis_row, min(next_row, axis_row + MAX_AXIS_DISTANCE), axis,
        ))
    results.sort(
        key=lambda item: (overall(item["metric"]), business_priority(item["metric"]), -item["row"]),
        reverse=True,
    )
    return [{key: value for key, value in item.items() if key != "row"}
            for item in results[:MAX_SERIES]]


def _worksheet_rows(regions):
    rows = defaultdict(dict)
    for region in regions:
        for source_row in region.get("analysis_rows") or region.get("preview_rows", []):
            for cell in source_row:
                address = str(cell.get("address", ""))
                if not address:
                    continue
                column, row = _coordinates(address)
                raw = _raw(cell)
                if raw not in (None, ""):
                    rows[row][column] = {
                        "cell": address, "value": raw,
                        "number_format": cell.get("number_format"),
                    }
    return rows


def _axes(row, cells, rows):
    headings = rows.get(row - 1, {})
    dates = axis_dates(row, cells, rows)
    dated = [(column, cell, dates[column])
             for column, cell in sorted(cells.items()) if column in dates]
    runs = []
    current, basis = [], None
    for column, cell, date in dated:
        heading = headings.get(column, {}).get("value")
        heading = heading if isinstance(heading, str) and not date_value(heading) else None
        if current and (column != current[-1][0] + 1 or heading and heading != basis):
            runs.append(current)
            current = []
        if not current or heading:
            basis = heading
        current.append((column, cell, date))
    if current:
        runs.append(current)
    return [(row, sorted(run, key=lambda point: point[2])) for run in runs if len(run) >= 2]


def _axis_series(rows, start, end, axis):
    results, scope = [], None
    first_column = min(point[0] for point in axis)
    basis = _basis(rows.get(start - 1, {}), axis)
    declared_unit = declared_axis_unit(rows, start)
    for row in sorted(number for number in rows if start < number < end):
        cells = rows[row]
        labels = _labels(cells, rows.get(start, {}), first_column)
        label = labels[0] if labels else None
        supported_axis = _supported_span(cells, axis)
        points = [
            {
                "period": date.isoformat(), "period_cell": date_cell["cell"],
                "period_label": period_label(date_cell["value"]),
                "value": cells[column]["value"], "value_cell": cells[column]["cell"],
                "number_format": cells[column].get("number_format"),
            }
            for column, date_cell, date in supported_axis
            if column in cells and finite(cells[column]["value"])
        ]
        axis_values = [cells[column] for column, _, _ in axis if column in cells]
        if label and len(points) >= 2 and len(points) == len(supported_axis) and len({unit(point) for point in points}) == 1:
            unique = {}
            for point in points:
                period = point["period"]
                if period in unique and unique[period]["value"] != point["value"]:
                    break
                unique.setdefault(period, point)
            else:
                points = list(unique.values())
                if len(points) >= 2:
                    results.append({
                        "metric": " · ".join(dict.fromkeys(" ".join(str(item["value"]).split()) for item in labels)),
                        "label_cell": label["cell"], "scope": scope["value"] if scope else None,
                        "label_cells": [item["cell"] for item in labels],
                        "scope_cell": scope["cell"] if scope else None,
                        "basis": basis["value"] if basis else None,
                        "basis_cell": basis["cell"] if basis else None,
                        "declared_unit": declared_unit,
                        "axis_period_count": len(axis),
                        "points": [points[0], points[-1]], "observations": points, "row": row,
                    })
        elif label and not axis_values:
            scope = label
    return results


def _supported_span(cells, axis):
    """Allow explicitly unavailable edge periods, never bridge an interior gap."""
    known = [index for index, (column, _, _) in enumerate(axis)
             if column in cells and finite(cells[column]["value"])]
    if len(known) < 2:
        return []
    first, last = known[0], known[-1]
    outside = [column for index, (column, _, _) in enumerate(axis) if index < first or index > last]
    missing = {"", "-", "--", "—", "n/a", "na", "not available", "no data"}
    if any(column in cells and str(cells[column]["value"]).strip().casefold() not in missing
           for column in outside):
        return []
    return axis[first:last + 1]


def _labels(cells, headers, first_column):
    labels = []
    for column, cell in sorted(cells.items()):
        heading = str(headers.get(column, {}).get("value", ""))
        if column >= first_column or not isinstance(cell["value"], str):
            continue
        if (not is_presentable_label(cell["value"])
                or heading and is_identifier_label(heading)
                or re.fullmatch(r"geography|type|kind|유형|종류", heading, re.I)):
            continue
        labels.append(cell)
    return labels


def _basis(cells, axis):
    return next((cells[column] for column, _, _ in axis
                 if column in cells and isinstance(cells[column]["value"], str)
                 and is_presentable_label(cells[column]["value"])), None)


def _raw(cell):
    return cell.get("cached_value") if cell.get("formula") else cell.get("value")


def _coordinates(address):
    column, row = coordinate_from_string(address.replace("$", ""))
    return column_index_from_string(column), row
