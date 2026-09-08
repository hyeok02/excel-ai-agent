"""Rejoin separated table regions without crossing an independent table boundary."""
from collections import defaultdict

from openpyxl.utils.cell import coordinate_from_string, column_index_from_string


def adjacent_date_regions(regions, is_date):
    results = []
    for header in regions:
        header_cells = _cells(header)
        header_bounds = _bounds(header_cells)
        if not header_bounds:
            continue
        for label_column, date_columns in _header_scopes(header_cells, is_date):
            columns = {label_column, *date_columns}
            for body in regions:
                body_bounds = _bounds(_cells(body))
                if (not body_bounds or body_bounds[0] != header_bounds[1] + 1
                        or not _structured_body(body, label_column, date_columns)):
                    continue
                results.append({
                    "title": header.get("title"), "role": "data",
                    "rows": [*_slice_rows(header, columns), *_slice_rows(body, columns)],
                })
    return results


def transposed_region(regions, is_date):
    bands = _bands(regions)
    for band_index, (bounds, stripes) in enumerate(bands):
        for label_column, date_columns in _header_scopes(_stripe_cells(stripes), is_date):
            columns = {label_column, *date_columns}
            selected = [_select_stripes(stripes, columns)]
            for later_bounds, later in bands[band_index + 1:]:
                if later_bounds[0] <= bounds[1]:
                    continue
                scoped = _select_stripes(later, columns)
                if len(scoped) != len(columns):
                    continue
                if _header_scopes(_stripe_cells(scoped), is_date):
                    break
                if _structured_stripes(scoped, label_column, date_columns):
                    selected.append(scoped)
            rows = _merge_stripes([stripe for group in selected for stripe in group])
            if _structured_rows(rows, label_column, date_columns):
                return {"title": None, "role": "data", "rows": rows}
    return None


def _header_scopes(cells, is_date):
    rows = defaultdict(list)
    for cell in cells:
        rows[_row(cell)].append(cell)
    scopes = []
    for row in rows.values():
        ordered = sorted(row, key=_column)
        labels = [cell for cell in ordered if isinstance(cell.get("value"), str)
                  and not is_date(cell.get("value"))]
        dates = [cell for cell in ordered if is_date(cell.get("value"))]
        for index, label in enumerate(labels):
            boundary = _column(labels[index + 1]) if index + 1 < len(labels) else 10**6
            date_columns = {_column(cell) for cell in dates
                            if _column(label) < _column(cell) < boundary}
            if len(date_columns) >= 2:
                scopes.append((_column(label), date_columns))
    return scopes


def _bands(regions):
    grouped = defaultdict(list)
    for region in regions:
        cells = _cells(region)
        columns = {_column(cell) for cell in cells}
        bounds = _bounds(cells)
        if len(columns) == 1 and bounds:
            grouped[bounds].append({"column": next(iter(columns)), "cells": cells})
    return sorted(grouped.items())


def _structured_body(region, label_column, date_columns):
    return _structured_rows(_slice_rows(region, {label_column, *date_columns}),
                            label_column, date_columns)


def _structured_stripes(stripes, label_column, date_columns):
    return _structured_rows(_merge_stripes(stripes), label_column, date_columns)


def _structured_rows(rows, label_column, date_columns):
    for row in rows:
        mapped = {_column(cell): cell for cell in row}
        label = mapped.get(label_column)
        if (label and isinstance(label.get("value"), str)
                and len(date_columns & set(mapped)) >= 2):
            return True
    return False


def _select_stripes(stripes, columns):
    return [stripe for stripe in stripes if stripe["column"] in columns]


def _slice_rows(region, columns):
    return [[cell for cell in row if _column(cell) in columns]
            for row in region.get("rows", [])
            if any(_column(cell) in columns for cell in row)]


def _merge_stripes(stripes):
    rows = defaultdict(list)
    for stripe in stripes:
        for cell in stripe["cells"]:
            rows[_row(cell)].append(cell)
    return [sorted(rows[number], key=_column) for number in sorted(rows)]


def _stripe_cells(stripes):
    return [cell for stripe in stripes for cell in stripe["cells"]]


def _cells(region):
    return [cell for row in region.get("rows", []) for cell in row]


def _bounds(cells):
    rows = [_row(cell) for cell in cells]
    return (min(rows), max(rows)) if rows else None


def _column(cell):
    return column_index_from_string(coordinate_from_string(cell["cell"])[0])


def _row(cell):
    return coordinate_from_string(cell["cell"])[1]
