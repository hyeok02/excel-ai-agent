from app.agent.query.comparison_scope import (
    question_date_bounds,
    rank_changes,
    requested_change_direction,
)
from app.agent.query.index import IndexedRow
from app.agent.tools.workbook_comparison_metrics import metric_changes
from app.agent.tools.workbook_comparison_series import time_series_candidates
from app.agent.tools.workbook_headers import HeaderContext


def build_time_series_comparison(
    rows: list[IndexedRow],
    headers: HeaderContext,
    query: str,
    metric_group: str | None = None,
    scoped_columns: dict[str, dict[str, tuple[str, ...]]] | None = None,
) -> dict[str, object] | None:
    candidates = time_series_candidates(rows, headers, question_date_bounds(query))
    if not candidates:
        return None
    selected = _best_candidate(rows, headers, candidates, scoped_columns or {})
    if selected is None:
        return None
    (sheet_name, date_column), points, metrics, scoped = selected
    start_date, start_row = points[0]
    end_date, end_row = points[-1]
    direction = requested_change_direction(query)
    ranked = rank_changes(metrics, direction)
    return {
        "sheet_name": sheet_name,
        "start_date": start_date.date().isoformat(),
        "end_date": end_date.date().isoformat(),
        "start_reference": f"{sheet_name}!{date_column}{start_row.row_number}",
        "end_reference": f"{sheet_name}!{date_column}{end_row.row_number}",
        "metric_group": metric_group if scoped else None,
        "change_direction": direction,
        "metrics": metrics,
        "ranked_changes": ranked[:5],
        "largest_absolute_changes": sorted(
            metrics, key=lambda item: abs(item["change"]), reverse=True
        )[:5],
    }


def time_series_calculations(
    comparison: dict[str, object] | None,
) -> list[dict[str, object]]:
    if not comparison or not isinstance(comparison.get("metrics"), list):
        return []
    calculations = []
    metrics = comparison.get("ranked_changes")
    if not metrics:
        metrics = comparison.get("largest_absolute_changes") or comparison["metrics"]
    for metric in metrics:
        if not isinstance(metric, dict):
            continue
        start = metric.get("start_value")
        end = metric.get("end_value")
        references = [metric.get("start_reference"), metric.get("end_reference")]
        numeric = all(
            isinstance(item, (int, float)) and not isinstance(item, bool)
            for item in (start, end)
        )
        if not all(isinstance(item, str) for item in references) or not numeric:
            continue
        common = {
            "operand_references": references,
            "operand_values": [start, end],
            "label": metric.get("header"),
        }
        calculations.append(
            {
                **common,
                "operation": "difference",
                "result": metric.get("change"),
                "unit": "source_unit",
            }
        )
        if float(start) != 0:
            calculations.append(
                {
                    **common,
                    "operation": "percent_change",
                    "result": (float(end) - float(start)) / abs(float(start)) * 100,
                    "unit": "percent",
                }
            )
    return calculations


def _best_candidate(
    rows: list[IndexedRow],
    headers: HeaderContext,
    candidates: list,
    scoped_columns: dict[str, dict[str, tuple[str, ...]]],
):
    valid = []
    for key, points in candidates:
        sheet_name, date_column = key
        start_row, end_row = points[0][1], points[-1][1]
        allowed = scoped_columns.get(sheet_name)
        if scoped_columns and allowed is None:
            continue
        metrics = metric_changes(
            rows,
            start_row,
            end_row,
            min(row.row_number for _, row in points),
            date_column,
            headers,
            allowed,
        )
        if metrics:
            valid.append((key, points, metrics, bool(allowed)))
    return max(valid, key=lambda item: len(item[1])) if valid else None
