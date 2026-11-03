"""Expose explicit, unfiltered native pivot totals as optional unit evidence.

This module does not infer units or trust a matching number alone. Consumers
must match the full source range and independently recompute its measure total.
"""

import math

from openpyxl.utils.cell import get_column_letter, quote_sheetname, range_boundaries


def pivot_unit_sources(workbook, worksheet, value_worksheet):
    sources = []
    for pivot in getattr(worksheet, "_pivots", ()):
        try:
            source = _pivot_source(workbook, worksheet, value_worksheet, pivot)
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            # Optional evidence must not prevent ordinary workbook analysis.
            continue
        if source is not None:
            sources.append(source)
            if len(sources) >= 64:
                break
    return sources


def _pivot_source(workbook, worksheet, values, pivot):
    if (len(pivot.dataFields) != 1 or pivot.pageFields or pivot.filters
            or not pivot.rowGrandTotals or not pivot.colGrandTotals):
        return None
    field = pivot.dataFields[0]
    if field.subtotal != "sum" or field.showDataAs != "normal":
        return None
    cache = pivot.cache
    if (cache.cacheSource.type != "worksheet" or cache.calculatedItems
            or cache.calculatedMembers
            or any(getattr(item, "formula", None) for item in cache.cacheFields)
            or any(item.h for axis in pivot.pivotFields for item in axis.items)):
        return None
    source = _worksheet_source(workbook, cache.cacheSource.worksheetSource)
    if source is None:
        return None
    source_sheet, reference = source
    bounds = _bounds(reference, source_sheet)
    if bounds is None:
        return None
    left, top, right, bottom = bounds
    if (bottom <= top or len(cache.cacheFields) != right - left + 1
            or not isinstance(field.fld, int) or not 0 <= field.fld < len(cache.cacheFields)):
        return None
    column = left + field.fld
    header = source_sheet.cell(top, column)
    cached_header = cache.cacheFields[field.fld].name
    if (header.data_type == "f" or not isinstance(header.value, str)
            or not isinstance(cached_header, str)
            or header.value.strip().casefold() != cached_header.strip().casefold()):
        return None
    total = _grand_total(worksheet, pivot)
    if total is None:
        return None
    raw = values[total.coordinate].value
    if (total.data_type == "f" or isinstance(raw, bool)
            or not isinstance(raw, (int, float)) or not math.isfinite(raw)):
        return None
    number_format = total.number_format
    if not isinstance(number_format, str) or not number_format.strip():
        return None
    return {
        "source_sheet": source_sheet.title,
        "source_range": f"{get_column_letter(left)}{top}:{get_column_letter(right)}{bottom}",
        "source_column": get_column_letter(column),
        "source_header": header.value,
        "total_value": raw,
        "total_cell": total.coordinate,
        "number_format": number_format,
        "reference": f"{quote_sheetname(worksheet.title)}!{total.coordinate}",
    }


def _worksheet_source(workbook, source):
    if source is None:
        return None
    if source.name and not source.ref:
        matches = [
            (sheet, table) for sheet in workbook.worksheets for table in sheet.tables.values()
            if table.name == source.name and (not source.sheet or source.sheet == sheet.title)
        ]
        if len(matches) != 1:
            return None
        sheet, table = matches[0]
        if table.headerRowCount != 1 or table.totalsRowCount:
            return None
        return sheet, table.ref
    if source.sheet and source.ref and not source.name and source.sheet in workbook.sheetnames:
        return workbook[source.sheet], source.ref
    return None


def _grand_total(sheet, pivot):
    bounds = _bounds(pivot.location.ref, sheet)
    if bounds is None or not pivot.rowItems or not pivot.colItems:
        return None
    left, top, right, bottom = bounds
    if (pivot.rowFields and pivot.rowItems[-1].t != "grand"
            or pivot.colFields and pivot.colItems[-1].t != "grand"):
        return None
    if (not pivot.rowFields and len(pivot.rowItems) != 1
            or not pivot.colFields and len(pivot.colItems) != 1):
        return None
    # Only use layouts whose native item counts locate the displayed grand total.
    if (top + pivot.location.firstDataRow + len(pivot.rowItems) - 1 != bottom
            or left + pivot.location.firstDataCol + len(pivot.colItems) - 1 != right):
        return None
    return sheet.cell(bottom, right)


def _bounds(reference, sheet):
    bounds = range_boundaries(reference)
    if any(not isinstance(value, int) for value in bounds):
        return None
    left, top, right, bottom = bounds
    if not (1 <= left <= right <= min(sheet.max_column, 16384)
            and 1 <= top <= bottom <= min(sheet.max_row, 1048576)):
        return None
    return bounds
