"""Extract metric series whose dates run horizontally across worksheet regions."""
from collections import defaultdict

from openpyxl.utils.cell import coordinate_from_string, column_index_from_string

from app.services.insights.display.display_quality import business_priority, is_presentable_label
from app.services.insights.facts.fact_trends import date_value
from app.services.insights.narratives.narrative_values import finite

MAX_SERIES = 24
MAX_AXIS_DISTANCE = 120


def extract_horizontal_series(regions):
    rows = _worksheet_rows(regions)
    axes = [axis for row, cells in sorted(rows.items()) for axis in _axes(row, cells)]
    results = []
    for axis_row, axis in axes:
        next_row = min((row for row, _ in axes if row > axis_row), default=10**9)
        results.extend(_axis_series(
            rows, axis_row, min(next_row, axis_row + MAX_AXIS_DISTANCE), axis,
        ))
    results.sort(
        key=lambda item: (business_priority(item["metric"]), -item["row"]),
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


def _axes(row, cells):
    dated = [(column, cell, date_value(cell["value"]))
             for column, cell in sorted(cells.items()) if date_value(cell["value"])]
    runs = []
    current = []
    for column, cell, date in dated:
        if current and (column != current[-1][0] + 1 or date <= current[-1][2]):
            runs.append(current)
            current = []
        current.append((column, cell, date))
    if current:
        runs.append(current)
    return [(row, run) for run in runs if len(run) >= 2]


def _axis_series(rows, start, end, axis):
    results, scope = [], None
    first_column = axis[0][0]
    basis = _basis(rows.get(start - 1, {}), axis)
    for row in sorted(number for number in rows if start < number < end):
        cells = rows[row]
        label = next((cell for column, cell in sorted(cells.items())
                      if column < first_column and isinstance(cell["value"], str)
                      and is_presentable_label(cell["value"])), None)
        points = [
            {
                "period": date.isoformat(), "period_cell": date_cell["cell"],
                "value": cells[column]["value"], "value_cell": cells[column]["cell"],
                "number_format": cells[column].get("number_format"),
            }
            for column, date_cell, date in axis
            if column in cells and finite(cells[column]["value"])
        ]
        axis_values = [cells[column] for column, _, _ in axis if column in cells]
        if label and len(points) >= 2:
            points = [points[0], points[-1]]
            results.append({
                "metric": " ".join(str(label["value"]).split()),
                "label_cell": label["cell"], "scope": scope["value"] if scope else None,
                "scope_cell": scope["cell"] if scope else None,
                "basis": basis["value"] if basis else None,
                "points": points, "row": row,
            })
        elif label and not axis_values:
            scope = label
    return results


def _basis(cells, axis):
    return next((cells[column] for column, _, _ in axis
                 if column in cells and isinstance(cells[column]["value"], str)
                 and is_presentable_label(cells[column]["value"])), None)


def _raw(cell):
    return cell.get("cached_value") if cell.get("formula") else cell.get("value")


def _coordinates(address):
    column, row = coordinate_from_string(address.replace("$", ""))
    return column_index_from_string(column), row
